/* Structured byte regions with a runtime word bound. Named arrays establish
 * disjoint storage; unknown pointers, calls, volatile observations and exits
 * retain the ordinary emitter. X/Y carry induction views, never C object data
 * across a call. Private index homes stay synchronized for arbitrary gathers. */
typedef struct {
    Statement *statement;Symbol *index;Expr *bound,*index_step;
    unsigned strides[16],uses[16],count,scale,limit,byte_ops;
    int primary_y,conditional,gather,expr_bound,needs_index_home;
} ByteLoopPlan;
typedef struct { ByteLoopPlan *plan;int borrowed;Symbol *x_value;unsigned stacked; } ByteLoopEmit;
typedef struct { Symbol *scalar;IndexedOperand array; } ByteLoopAddress;
static int byte_loop_target(ByteLoopPlan *p,Expr *e);

static int byte_loop_home(Symbol *s)
{
    return !s->owner||(cg.dp_homes&&s->offset&&(s->offset&1)&&
           (s->offset-1)/2<cg.dp_words&&cg.dp_map[(s->offset-1)/2]);
}
static int byte_loop_affine(ByteLoopPlan *p,IndexedOperand *operand,unsigned *stride,unsigned *offset)
{
    unsigned a,b,g;
    if(!retained_affine_for(operand->index,p->index,&a,&b)||!a||
       a>65535/operand->scale||b>65535/operand->scale)return 0;
    *stride=a*operand->scale;*offset=b*operand->scale+operand->offset;
    if(*offset>65535)return 0;
    /* A running displacement wraps modulo 65536. Folding a constant is safe
     * either over a proved finite span, or inside the stride's low zero bits. */
    g=*stride&(~*stride+1u);
    return *offset<g||(p->limit&&p->limit<=65535&&
           (p->limit<=1||*stride<=(65535-*offset)/(p->limit-1)));
}
static int byte_loop_pure(ByteLoopPlan *p,Expr *e)
{
    IndexedOperand operand;unsigned stride,offset,i;
    if(!e||volatile_expression(e)||e->type.pointers||e->type.array||
       e->type.base==TY_FLOAT||reg_width(e->type)>2)return 0;
    if(e->kind==EX_INT)return 1;
    if(e->kind==EX_OBJECT)return byte_loop_home(e->symbol);
    if(indexed_operand(e,&operand)){
        if(byte_loop_affine(p,&operand,&stride,&offset)){
            for(i=0;i<p->count&&p->strides[i]!=stride;++i){}
            if(i==p->count&&i<16){p->strides[i]=stride;p->uses[i]=0;++p->count;}
            if(i<16)++p->uses[i];
        }else p->gather=1;
        return byte_loop_pure(p,operand.index);
    }
    if(e->kind==EX_CAST||e->kind==EX_UNARY)return byte_loop_pure(p,e->left);
    if(e->kind!=EX_BINARY)return 0;
    return (basic_integer_op(e->op)||comparison(e->op)||e->op==TOK_LAND||e->op==TOK_LOR||
        e->op=='*'||e->op=='/'||e->op=='%'||e->op==TOK_SHL||e->op==TOK_SHR)&&
        byte_loop_pure(p,e->left)&&byte_loop_pure(p,e->right);
}
static Expr *byte_loop_bits(Expr *e)
{
    while(e->kind==EX_CAST&&!e->type.is_bool&&!e->type.pointers&&reg_width(e->type)==2)e=e->left;
    return e;
}
static Expr *byte_loop_test_bits(Expr *e)
{
    /* A byte cast selects a new sign extension for comparison. Word casts
     * preserve its bits; the final common type determines signed ordering. */
    while(e->kind==EX_CAST&&!e->type.is_bool&&!e->type.pointers&&
          e->type.base==TY_INT&&width(e->type)==2)e=e->left;
    return e;
}
static int byte_loop_mapped(ByteLoopPlan *p,IndexedOperand *operand)
{
    unsigned stride,offset;
    if(!byte_loop_affine(p,operand,&stride,&offset))return 0;
    if(stride==1)operand->reg=p->primary_y?'y':'x';
    else if(!p->primary_y&&stride==p->scale)operand->reg='y';
    else return 0;
    operand->offset=offset;return 1;
}
static int byte_loop_simple(ByteLoopPlan *p,Expr *e)
{
    IndexedOperand operand;
    e=byte_loop_bits(e);
    if(e->kind==EX_INT||e->kind==EX_OBJECT)return 1;
    if(indexed_operand(e,&operand))return byte_loop_mapped(p,&operand);
    return 0;
}
static int byte_loop_condition(ByteLoopPlan *p,Expr *e)
{
    Expr *a,*b;uint32_t value;
    if(!e||volatile_expression(e))return 0;
    if(e->kind==EX_ASSIGN)return !e->op&&e->left->kind==EX_OBJECT&&
        e->left->symbol->owner==cg.function->id&&width(e->left->type)==2&&
        byte_loop_target(p,e->left)&&byte_loop_pure(p,e->right)&&unsigned_byte_value(e);
    if(e->kind==EX_COMMA){Expr *set=e->left;
        return set->kind==EX_ASSIGN&&!set->op&&set->left->kind==EX_OBJECT&&
            set->left->symbol->owner==cg.function->id&&width(set->left->type)==2&&
            byte_loop_target(p,set->left)&&byte_loop_pure(p,set->right)&&byte_loop_condition(p,e->right);
    }
    if(e->kind==EX_UNARY&&e->op=='!')return byte_loop_condition(p,e->left);
    if(e->kind!=EX_BINARY||!comparison(e->op))
        return (width(byte_loop_test_bits(e)->type)==1||unsigned_byte_value(e))&&
               byte_loop_simple(p,e)&&byte_loop_pure(p,e);
    a=byte_loop_test_bits(e->left);b=byte_loop_test_bits(e->right);
    if(width(a->type)!=1||!byte_loop_simple(p,a)||!byte_loop_pure(p,a))return 0;
    if(integer_constant(b,&value)){
        if(a->type.is_unsigned){if(value>255)return 0;}
        else if((int32_t)value < -128||(int32_t)value>127)return 0;
    }else if(width(b->type)!=1||a->type.is_unsigned!=b->type.is_unsigned||
             !byte_loop_simple(p,b)||!byte_loop_pure(p,b))return 0;
    return 1;
}
static int byte_loop_condition_inputs(ByteLoopPlan *p,Expr *e)
{
    if(e->kind==EX_ASSIGN)return !e->op&&e->left->kind==EX_OBJECT&&
        e->left->symbol->owner==cg.function->id&&width(e->left->type)==2&&
        byte_loop_target(p,e->left)&&byte_loop_pure(p,e->right)&&unsigned_byte_value(e);
    if(e->kind==EX_COMMA){Expr *set=e->left;
        return set->kind==EX_ASSIGN&&!set->op&&set->left->kind==EX_OBJECT&&
            set->left->symbol->owner==cg.function->id&&width(set->left->type)==2&&
            byte_loop_target(p,set->left)&&byte_loop_pure(p,set->right)&&byte_loop_condition_inputs(p,e->right);
    }
    if(e->kind==EX_UNARY&&e->op=='!')return byte_loop_condition_inputs(p,e->left);
    if(e->kind==EX_BINARY&&comparison(e->op))return byte_loop_pure(p,e->left)&&byte_loop_pure(p,e->right);
    return byte_loop_pure(p,e);
}
static int byte_loop_target(ByteLoopPlan *p,Expr *e)
{
    IndexedOperand operand;
    if(!e||volatile_expression(e)||e->type.is_bool)return 0;
    if(e->kind==EX_OBJECT)return e->symbol!=p->index&&
        !loop_mentions(p->bound,e->symbol)&&byte_loop_home(e->symbol);
    return width(e->type)==1&&indexed_operand(e,&operand)&&byte_loop_pure(p,operand.index);
}
static int byte_loop_effect(ByteLoopPlan *p,Expr *e)
{
    Expr *rhs;
    if(e==p->index_step)return 1;
    if(e->kind==EX_COMMA)return byte_loop_effect(p,e->left)&&byte_loop_effect(p,e->right);
    if(e->kind==EX_ASSIGN){
        if(!byte_loop_target(p,e->left)||reg_width(e->type)!=2)return 0;
        if(width(e->type)==1){
            if(e->op&&!basic_integer_op(e->op))return 0;
            if(!byte_loop_pure(p,e->right))return 0;
            ++p->byte_ops;
            return 1;
        }
        if(e->left->kind!=EX_OBJECT||e->left->type.pointers||e->left->type.base!=TY_INT)return 0;
        rhs=byte_loop_bits(e->right);
        if(!e->op&&(rhs->kind==EX_POST||rhs->kind==EX_PRE))
            return rhs->left->kind==EX_OBJECT&&width(rhs->type)==2&&
                   byte_loop_target(p,rhs->left)&&direct_increment(rhs);
        return (!e->op||basic_integer_op(e->op))&&byte_loop_pure(p,e->right);
    }
    if(e->kind==EX_POST||e->kind==EX_PRE)
        return byte_loop_target(p,e->left)&&e->left->kind==EX_OBJECT&&
               direct_increment(e)&&!e->type.pointers;
    return 0;
}
static int byte_loop_statements(ByteLoopPlan *p,Statement *s,int predicates)
{
    for(;s;s=s->next){Expr *e=s->expression;
        if(s->kind==ST_BLOCK){if(!byte_loop_statements(p,s->body,predicates))return 0;continue;}
        if(s->kind==ST_EMPTY)continue;
        if(s->kind==ST_IF){
            p->conditional=1;
            if(predicates&&!byte_loop_condition(p,e))return 0;
            if(!predicates&&!byte_loop_condition_inputs(p,e))return 0;
            if(!byte_loop_statements(p,s->body,predicates)||!byte_loop_statements(p,s->alternate,predicates))return 0;
            continue;
        }
        if(s->kind!=ST_EXPR||!e||!byte_loop_effect(p,e))return 0;
    }return 1;
}
static void byte_loop_borrow(ByteLoopEmit *e)
{
    if(!e->plan->primary_y&&!e->borrowed){code("    phx\n");e->borrowed=1;}
}
static void byte_loop_release(ByteLoopEmit *e)
{
    if(e->borrowed){code("    plx\n");e->borrowed=0;}e->x_value=NULL;
}
static void byte_loop_word(ByteLoopEmit *e,Expr *value);
static ByteLoopAddress byte_loop_address(ByteLoopEmit *e,Expr *value)
{
    ByteLoopAddress address={0};IndexedOperand *operand=&address.array;
    if(value->kind==EX_OBJECT){address.scalar=value->symbol;return address;}
    if(!indexed_operand(value,operand))error_at(value->location,"internal byte region address");
    if(byte_loop_mapped(e->plan,operand)&&!(operand->reg=='x'&&e->borrowed))return address;
    byte_loop_borrow(e);operand->reg='x';
    if(operand->scale==1&&operand->index->kind==EX_OBJECT&&width(operand->index->type)==2){
        Symbol *index=operand->index->symbol;
        if(e->x_value!=index){code("    ldx ");array_operand(index,0);code("\n");e->x_value=index;}
    }else{
        byte_loop_word(e,operand->index);
        if(operand->scale!=1)strength_scale(operand->scale,operand->index);
        code("    tax\n    sep #$20\n.a8\n");e->x_value=NULL;
    }
    return address;
}
static void byte_loop_operand(ByteLoopAddress *address)
{
    if(address->scalar)array_operand(address->scalar,0);else indexed_text(&address->array);
}
static int byte_loop_clobbers_x(ByteLoopEmit *e,Expr *value)
{
    IndexedOperand operand;Expr *v=byte_loop_bits(value);
    if(v->kind==EX_INT||v->kind==EX_OBJECT)return 0;
    if(indexed_operand(v,&operand))return !byte_loop_mapped(e->plan,&operand)||
        (operand.reg=='x'&&e->borrowed);
    if(v->kind==EX_UNARY&&(v->op=='~'||v->op=='-'||v->op=='+'))return byte_loop_clobbers_x(e,v->left);
    if(v->kind==EX_BINARY&&basic_integer_op(v->op)&&v->right->kind==EX_INT)
        return byte_loop_clobbers_x(e,v->left);
    return 1;
}
static void byte_loop_value(ByteLoopEmit *e,Expr *value)
{
    Expr *v=byte_loop_bits(value);ByteLoopAddress address;ShiftIndex shift;uint32_t values[16];unsigned i,id;
    if(v->kind==EX_INT){code("    lda #$%02X\n",v->value&255);return;}
    if(v->kind==EX_OBJECT&&v->symbol==e->plan->index){
        if(e->plan->primary_y)code("    tya\n");
        else if(!e->borrowed)code("    txa\n");
        else code("    lda %u,s\n",1+e->stacked);return;
    }
    if(v->kind==EX_OBJECT||v->kind==EX_DEREF||v->kind==EX_MEMBER){
        address=byte_loop_address(e,v);code("    lda ");byte_loop_operand(&address);code("\n");return;
    }
    if(v->kind==EX_UNARY&&(v->op=='~'||v->op=='-'||v->op=='+')){
        byte_loop_value(e,v->left);
        if(v->op!='+')code("    eor #$FF\n");if(v->op=='-')code("    inc a\n");return;
    }
    if(v->kind==EX_BINARY&&basic_integer_op(v->op)&&v->right->kind==EX_INT){
        byte_loop_value(e,v->left);if(v->op=='+'||v->op=='-')code(v->op=='+'?"    clc\n":"    sec\n");
        code("    %s #$%02X\n",v->op=='+'?"adc":v->op=='-'?"sbc":v->op=='&'?"and":v->op=='|'?"ora":"eor",v->right->value&255);return;
    }
    if(v->kind==EX_BINARY&&bounded_shift_values(v->left,v->right,v->op,&shift,values)){
        Expr *inp=byte_loop_bits(shift.input);
        byte_loop_borrow(e);id=++cg.label;
        if(inp->kind==EX_OBJECT&&inp->symbol==e->plan->index){
            code("; bounded byte shift lookup\n    rep #$20\n.a16\n");
            byte_loop_value(e,shift.input);
        }else{
            byte_loop_value(e,shift.input);
            code("; bounded byte shift lookup\n    rep #$20\n.a16\n");
        }
        code("    and #$%04X\n    tax\n"
             "    sep #$20\n.a8\n    lda f:byte_shift_%s_%u,x\n",shift.mask,cg.parser->unit,id);
        code(".segment \"RODATA\"\nbyte_shift_%s_%u:\n    .byte ",cg.parser->unit,id);
        for(i=0;i<=shift.mask;++i)code("%s$%02X",i?",":"",values[i]&255);
        code("\n.segment \"%s\"\n",code_segment());e->x_value=NULL;return;
    }
    byte_loop_borrow(e);code("    rep #$20\n.a16\n    phy\n");emit_value(value);
    code("    ply\n    sep #$20\n.a8\n");e->x_value=NULL;
}
/* Return a full promoted word, starting in A8. Common gather/scatter address
 * arithmetic keeps a mapped byte load in Y instead of rebuilding its index. */
static void byte_loop_word(ByteLoopEmit *e,Expr *value)
{
    Expr *v=value,*left,*right;uint32_t constant;
    while(v->kind==EX_CAST&&width(v->type)==2&&width(v->left->type)==2)v=v->left;
    left=v->left;right=v->right;
    if(v->kind==EX_BINARY&&(v->op=='+'||v->op=='*'||v->op=='&'||v->op=='|'||v->op=='^')&&
       integer_constant(left,&constant)&&!integer_constant(right,&constant)){left=v->right;right=v->left;}
    if(v->kind==EX_BINARY&&integer_constant(right,&constant)&&
       (basic_integer_op(v->op)||v->op=='*'||v->op=='/'||v->op=='%'||v->op==TOK_SHL||v->op==TOK_SHR)){
        byte_loop_word(e,left);binary_after_left(left,right,v->op);return;
    }
    if(width(v->type)==1){
        byte_loop_value(e,v);code("    rep #$20\n.a16\n");narrow_char(v->type);return;
    }
    code("    rep #$20\n.a16\n");
    if(v->kind==EX_OBJECT&&v->symbol==e->plan->index){
        if(e->plan->primary_y)code("    tya\n");else if(!e->borrowed)code("    txa\n");
        else code("    lda %u,s\n",1+e->stacked);return;
    }
    code("    phy\n");emit_value(value);code("    ply\n");e->x_value=NULL;
}
static void byte_loop_test(ByteLoopEmit *e,Expr *test,unsigned no,int invert)
{
    Expr *a,*b;ByteLoopAddress operand;uint32_t constant;int op,signed_order;
    if(test->kind==EX_ASSIGN){
        byte_loop_borrow(e);code("    rep #$20\n.a16\n    phy\n");emit_value(test);
        code("    ply\n    sep #$20\n.a8\n");e->x_value=NULL;byte_loop_release(e);
        code("    cmp #$00\n    %s cg_%s_%u\n",invert?"bne":"beq",cg.parser->unit,no);return;
    }
    if(test->kind==EX_COMMA){
        byte_loop_borrow(e);code("    rep #$20\n.a16\n    phy\n");emit_discarded(test->left);
        code("    ply\n    sep #$20\n.a8\n");e->x_value=NULL;byte_loop_release(e);
        byte_loop_test(e,test->right,no,invert);return;
    }
    if(test->kind==EX_UNARY&&test->op=='!'){byte_loop_test(e,test->left,no,!invert);return;}
    if(test->kind!=EX_BINARY||!comparison(test->op)){
        byte_loop_value(e,test);code("    %s cg_%s_%u\n",invert?"bne":"beq",cg.parser->unit,no);return;
    }
    a=byte_loop_test_bits(test->left);b=byte_loop_test_bits(test->right);op=test->op;
    if(invert)op=op==TOK_EQ?TOK_NE:op==TOK_NE?TOK_EQ:op=='<'?TOK_GE:op==TOK_GE?'<':op=='>'?TOK_LE:'>';
    signed_order=!a->type.is_unsigned&&!common_type(test->left->type,test->right->type).is_unsigned&&op!=TOK_EQ&&op!=TOK_NE;
    byte_loop_value(e,a);
    if(signed_order)code("    sec\n");
    if(integer_constant(b,&constant))code("    %s #$%02X\n",signed_order?"sbc":"cmp",constant&255);
    else{operand=byte_loop_address(e,byte_loop_bits(b));code("    %s ",signed_order?"sbc":"cmp");byte_loop_operand(&operand);code("\n");}
    if(signed_order){unsigned equal=0;
        if(op=='>')code("    beq cg_%s_%u\n",cg.parser->unit,no);
        else if(op==TOK_LE){equal=++cg.label;code("    beq cg_%s_%u\n",cg.parser->unit,equal);}
        code("    bvc :+\n    eor #$80\n:\n    %s cg_%s_%u\n",op=='<'||op==TOK_LE?"bpl":"bmi",cg.parser->unit,no);
        if(equal)label(equal);return;
    }
    if(op==TOK_EQ||op==TOK_NE||op=='<'||op==TOK_GE)
        code("    %s cg_%s_%u\n",op==TOK_EQ?"bne":op==TOK_NE?"beq":op=='<'?"bcs":"bcc",cg.parser->unit,no);
    else if(op=='>')code("    bcc cg_%s_%u\n    beq cg_%s_%u\n",cg.parser->unit,no,cg.parser->unit,no);
    else{unsigned yes=++cg.label;code("    bcc cg_%s_%u\n    bne cg_%s_%u\n",cg.parser->unit,yes,cg.parser->unit,no);label(yes);}
}
static void byte_loop_emit_effect(ByteLoopEmit *context,Expr *e)
{
    ByteLoopPlan *p=context->plan;
    if(e==p->index_step){
        byte_loop_release(context);
        if(p->needs_index_home){
            code(p->primary_y?"    iny\n    sty ":"    inx\n    stx ");
            array_operand(p->index,0);code("\n");
        }else{
            code(p->primary_y?"    iny\n":"    inx\n");
        }
        for(unsigned i=0;i<p->scale;++i)code("    iny\n");
        return;
    }
    if(e->kind==EX_COMMA){
        byte_loop_emit_effect(context,e->left);
        byte_loop_emit_effect(context,e->right);
        return;
    }
    if((e->kind==EX_PRE||e->kind==EX_POST)&&width(e->type)==1){
        Symbol *target=e->left->symbol;
        const char *op=e->op==TOK_INC?"inc":"dec";
        if(target->type.banked){
            code("    lda ");array_operand(target,0);
            code("\n    %s a\n    sta ",op);
        }else code("    %s ",op);
        array_operand(target,0);code("\n");
        if(target==context->x_value)context->x_value=NULL;
        return;
    }
    Expr *rhs;ByteLoopAddress address;int save;Symbol *cached;
    if(e->kind==EX_ASSIGN&&width(e->type)==1){
        address=byte_loop_address(context,e->left);
        save=!address.scalar&&address.array.reg=='x'&&byte_loop_clobbers_x(context,e->right);
        if(save){byte_loop_borrow(context);code("    phx\n");context->stacked+=2;}
        cached=context->x_value;
        if(e->op=='-'){
            /* Preserve source-order snapshot and full operand evaluation
             * for subtraction; other low-byte operations commute. */
            byte_loop_borrow(context);code("    rep #$20\n.a16\n    phy\n");emit_discarded(e);
            code("    ply\n    sep #$20\n.a8\n");context->x_value=NULL;
            if(save){code("    plx\n");context->stacked-=2;context->x_value=cached;}return;
        }
        byte_loop_value(context,e->right);
        if(save){code("    plx\n");context->stacked-=2;context->x_value=cached;}
        if(e->op){if(e->op=='+')code("    clc\n");code("    %s ",e->op=='+'?"adc":e->op=='&'?"and":e->op=='|'?"ora":"eor");byte_loop_operand(&address);code("\n");}
        code("    sta ");byte_loop_operand(&address);code("\n");
        if(address.scalar==context->x_value)context->x_value=NULL;
    }else{
        rhs=e->kind==EX_ASSIGN?byte_loop_bits(e->right):e;
        if((rhs->kind==EX_POST||rhs->kind==EX_PRE)&&width(rhs->type)==2&&
           rhs->left->kind==EX_OBJECT&&increment_step(rhs->type)==1){
            Symbol *source=rhs->left->symbol,*destination=e->kind==EX_ASSIGN?e->left->symbol:NULL;
            byte_loop_borrow(context);code("    ldx ");array_operand(source,0);code("\n");
            if(destination&&rhs->kind==EX_POST){code("    stx ");array_operand(destination,0);code("\n");}
            code(rhs->op==TOK_INC?"    inx\n":"    dex\n");code("    stx ");array_operand(source,0);code("\n");
            if(destination&&rhs->kind==EX_PRE){code("    stx ");array_operand(destination,0);code("\n");}
            if(destination&&rhs->kind==EX_POST)code(rhs->op==TOK_INC?"    dex\n":"    inx\n");
            context->x_value=destination?destination:source;
        }else{
            byte_loop_borrow(context);code("    rep #$20\n.a16\n    phy\n");emit_discarded(e);
            code("    ply\n    sep #$20\n.a8\n");context->x_value=NULL;
        }
    }
}
static void byte_loop_emit(ByteLoopEmit *context,Statement *s)
{
    Statement *previous=NULL;
    for(;s;previous=s,s=s->next){
        loop_current=s;loop_previous=previous;
        inline_marker(s);
        if(s->kind==ST_EMPTY)continue;
        if(s->kind==ST_BLOCK){byte_loop_emit(context,s->body);continue;}
        if(s->kind==ST_IF){unsigned no=++cg.label,done=++cg.label;
            byte_loop_release(context);byte_loop_test(context,s->expression,no,0);
            byte_loop_emit(context,s->body);byte_loop_release(context);
            if(s->alternate)jump(done);label(no);
            if(s->alternate){byte_loop_emit(context,s->alternate);byte_loop_release(context);label(done);}continue;
        }
        byte_loop_emit_effect(context,s->expression);
    }
}
static Expr *byte_loop_index_step(Expr *step,Symbol *index)
{
    uint32_t delta;
    if(step->kind==EX_COMMA){
        Expr *left=byte_loop_index_step(step->left,index);
        return left?left:byte_loop_index_step(step->right,index);
    }
    if(!(((step->kind==EX_PRE||step->kind==EX_POST)&&step->op==TOK_INC)||
         (step->kind==EX_ASSIGN&&step->op=='+'&&integer_constant(step->right,&delta)&&delta==1))||
       step->left->kind!=EX_OBJECT||step->left->symbol!=index)return NULL;
    return step;
}
static int byte_loop_invariant_bound(Statement *s,Expr *e)
{
    if(!e||volatile_expression(e)||body_effect(e)||e->type.pointers||e->type.array||
       e->type.base==TY_FLOAT||reg_width(e->type)>2)return 0;
    if(e->kind==EX_INT)return 1;
    if(e->kind==EX_OBJECT)
        return loop_private(e->symbol)&&byte_loop_home(e->symbol)&&
               !object_volatile(e->symbol->type)&&
               !scalar_writes(s->body,e->symbol)&&!scalar_writes_expr(s->step,e->symbol);
    if(e->kind==EX_CAST||e->kind==EX_UNARY)return byte_loop_invariant_bound(s,e->left);
    if(e->kind!=EX_BINARY||e->arg_count)return 0;
    return (basic_integer_op(e->op)||e->op=='*'||e->op=='/'||e->op=='%'||
            e->op==TOK_SHL||e->op==TOK_SHR)&&
           byte_loop_invariant_bound(s,e->left)&&byte_loop_invariant_bound(s,e->right);
}
static int byte_loop_expr_uses_fallback(ByteLoopPlan *p,Expr *e)
{
    IndexedOperand operand;ShiftIndex shift;uint32_t values[16],c;
    if(!e)return 0;
    if(e->kind==EX_INT)return 0;
    if(e->kind==EX_OBJECT)return 0;
    if(indexed_operand(e,&operand))return !byte_loop_mapped(p,&operand);
    if(e->kind==EX_CAST)return byte_loop_expr_uses_fallback(p,e->left);
    if(e->kind==EX_UNARY&&(e->op=='~'||e->op=='-'||e->op=='+'||e->op=='!'))
        return byte_loop_expr_uses_fallback(p,e->left);
    if(e->kind==EX_BINARY){
        if(comparison(e->op)){
            Expr *a=byte_loop_test_bits(e->left),*b=byte_loop_test_bits(e->right);
            return width(a->type)!=1||byte_loop_expr_uses_fallback(p,a)||
                   (!integer_constant(b,&c)&&byte_loop_expr_uses_fallback(p,b));
        }
        if(basic_integer_op(e->op)&&integer_constant(e->right,&c))
            return byte_loop_expr_uses_fallback(p,e->left);
        if(bounded_shift_values(e->left,e->right,e->op,&shift,values))
            return byte_loop_expr_uses_fallback(p,shift.input);
    }
    if(e->kind==EX_ASSIGN&&width(e->type)==1&&e->op!='-')
        return byte_loop_expr_uses_fallback(p,e->left)||byte_loop_expr_uses_fallback(p,e->right);
    return 1;
}
static int byte_loop_stmt_uses_fallback(ByteLoopPlan *p,Statement *s)
{
    for(;s;s=s->next){
        if(s->kind==ST_EMPTY)continue;
        if(s->kind==ST_BLOCK){if(byte_loop_stmt_uses_fallback(p,s->body))return 1;continue;}
        if(s->kind==ST_IF){
            if(byte_loop_expr_uses_fallback(p,s->expression)||
               byte_loop_stmt_uses_fallback(p,s->body)||
               byte_loop_stmt_uses_fallback(p,s->alternate))return 1;
            continue;
        }
        if(s->kind==ST_EXPR&&byte_loop_expr_uses_fallback(p,s->expression))return 1;
    }
    return 0;
}
static int structured_byte_loop(Statement *s)
{
    ByteLoopPlan plan={0};ByteLoopEmit emit={0};Expr *condition=s->expression,*step=s->step;
    Type t;uint32_t limit;unsigned i,best=0,enter,body,step_label,done;int constant,unsigned_cmp;
    Statement *previous=loop_previous,*current=loop_current;
    if(cg.parser->no_strength_reduction||cg.parser->no_body_optimizations||cg.parser->no_register_loops||
       cg.parser->no_register_cursors||cg.parser->no_indexed_operands||!cg.dp_homes||cg.stack_leaf||
       cg.function->jump_label_count||cg.retained_index||cg.numeric_index||cg.bound||cg.affine_active||
       cg.lftr_active||cg.scalar_first||cg.scalar_leaf||cg.loop_count==64||s->kind!=ST_FOR||
       !condition||condition->kind!=EX_BINARY||(condition->op!='<'&&condition->op!=TOK_NE)||
       condition->left->kind!=EX_OBJECT||!step)return 0;
    plan.statement=s;plan.index=condition->left->symbol;plan.bound=condition->right;
    t=common_type(condition->left->type,condition->right->type);
    if(t.base!=TY_INT||t.pointers||plan.index->type.base!=TY_INT||width(plan.index->type)!=2||
       !loop_private(plan.index)||!byte_loop_home(plan.index))return 0;
    constant=integer_constant(plan.bound,&limit);
    if(!constant&&!(plan.bound->kind==EX_OBJECT&&byte_loop_home(plan.bound->symbol)&&direct_operand(plan.bound,t,0,0))){
        if(!byte_loop_invariant_bound(s,plan.bound))return 0;
        plan.expr_bound=1;
    }else if(!direct_operand(plan.bound,t,0,0))return 0;
    for(i=0;i<cg.cursor_count;++i)if(cg.cursors[i].index==plan.index)return 0;
    plan.index_step=byte_loop_index_step(step,plan.index);
    if(!plan.index_step)return 0;
    /* A trailing step can index with the incremented counter at the bound */
    if(constant&&t.is_unsigned&&step==plan.index_step)plan.limit=limit;
    else if(step==plan.index_step&&plan.bound->known.valid&&plan.bound->known.min>=0&&
            plan.bound->known.max<=65535&&(t.is_unsigned||plan.bound->known.max<=32767))
        plan.limit=plan.bound->known.max?(unsigned)plan.bound->known.max:1;
    else plan.limit=65536;
    if(!byte_loop_statements(&plan,s->body,0)||!byte_loop_effect(&plan,step)||plan.byte_ops<1)return 0;
    if(constant&&!plan.conditional&&!plan.gather)return 0;
    for(i=0;i<plan.count;++i)if(plan.strides[i]>1&&plan.strides[i]<=8&&
       plan.uses[i]>best){plan.scale=plan.strides[i];best=plan.uses[i];}
    if(constant&&plan.scale>1&&!plan.gather)return 0;
    plan.primary_y=!plan.scale;
    if(!byte_loop_statements(&plan,s->body,1))return 0;
    plan.needs_index_home=plan.gather||step!=plan.index_step||
        loop_observed_outside(cg.function->body,s,plan.index)||
        byte_loop_stmt_uses_fallback(&plan,s->body);
    enter=++cg.label;body=++cg.label;step_label=++cg.label;done=++cg.label;
    unsigned_cmp=t.is_unsigned||condition->op==TOK_NE||
        (condition->left->known.valid&&condition->left->known.min>=0&&
         condition->right->known.valid&&condition->right->known.min>=0);
    code("; structured byte loop: %s, %s bound, %c=counter",plan.index->name,constant?"constant":"runtime",plan.primary_y?'Y':'X');
    if(!plan.primary_y)code(", Y=stride %u",plan.scale);code("\n");
    if(plan.expr_bound){
        emit_value(plan.bound);
        convert_registers(plan.bound->type,t);
        code("    pei ($00)\n    sta z:$0000\n");
        load_symbol(plan.index);
        if(condition->op==TOK_NE){
            code("    cmp z:$0000\n    bne :+\n");jump(done);code(":\n");
        }else if(unsigned_cmp){
            code("    cmp z:$0000\n    bcc :+\n");jump(done);code(":\n");
        }else{
            code("    sec\n    sbc z:$0000\n    bvc :+\n    eor #$8000\n:\n    bmi :+\n");jump(done);code(":\n");
        }
    }else branch(condition,enter,done,enter);
    label(enter);code("    phy\n");
    if(plan.primary_y){code("    ldy ");array_operand(plan.index,0);code("\n");}
    else{code("    ldx ");array_operand(plan.index,0);code("\n    txa\n");strength_scale(plan.scale,condition->left);code("    tay\n");}
    cg.loop_start[cg.loop_count]=step_label;cg.loop_end[cg.loop_count++]=done;
    code("    sep #$20\n.a8\n");label(body);emit.plan=&plan;byte_loop_emit(&emit,s->body);byte_loop_release(&emit);
    label(step_label);
    byte_loop_emit_effect(&emit,s->step);byte_loop_release(&emit);
    if(unsigned_cmp){
        code(plan.primary_y?"    cpy ":"    cpx ");
        if(plan.expr_bound)code("z:$0000");else direct_operand(plan.bound,t,0,1);
        code("\n    %s cg_%s_%u\n",condition->op==TOK_NE?"bne":"bcc",cg.parser->unit,body);
    }else{unsigned finish=++cg.label;
        code("    rep #$20\n.a16\n    %s\n    sec\n    sbc ",plan.primary_y?"tya":"txa");
        if(plan.expr_bound)code("z:$0000");else direct_operand(plan.bound,t,0,1);
        code("\n    bvc :+\n    eor #$8000\n:\n    bpl cg_%s_%u\n"
            "    sep #$20\n.a8\n",cg.parser->unit,finish);jump(body);label(finish);
    }
    code("    rep #$20\n.a16\n    ply\n");
    --cg.loop_count;label(done);
    if(plan.expr_bound)code("    pla\n    sta z:$0000\n");
    cg.divmod_available=0;
    loop_previous=previous;loop_current=current;return 1;
}

/* A finite, nonoverlapping byte copy can visit two bytes at once. The proof
 * covers object extents and both offsets; overlapping/volatile copies retain
 * their original byte ordering. Code growth uses the existing unroll budget. */
static int fixed_byte_copy_loop(Statement *s)
{
    Statement *body=s->body,*initial=s->initial;Expr *e,*init,*test=s->expression,*step=s->step,*rhs;
    IndexedOperand to,from;Symbol *index;uint32_t first,end;unsigned a,b,c,d,count,i,source,destination;
    if(cg.parser->no_strength_reduction||cg.parser->no_body_optimizations||cg.parser->no_loop_unroll||
       cg.parser->no_register_loops||cg.retained_index||cg.numeric_index||cg.affine_active||cg.lftr_active||
       cg.function->jump_label_count||s->kind!=ST_FOR||!test||test->kind!=EX_BINARY||test->op!='<'||
       test->left->kind!=EX_OBJECT||!integer_constant(test->right,&end)||!step)return 0;
    index=test->left->symbol;
    while(body&&body->kind==ST_BLOCK&&!body->next&&!body->inline_callee)body=body->body;
    while(initial&&initial->kind==ST_BLOCK&&!initial->next)initial=initial->body;
    if(!loop_private(index)||width(index->type)!=2||index->type.base!=TY_INT||index->type.pointers||
       reg_width(common_type(test->left->type,test->right->type))!=2||
       end>(index->type.is_unsigned?65535u:32767u)||
       !body||body->next||body->kind!=ST_EXPR||body->inline_callee||
       !initial||initial->next||initial->kind!=ST_EXPR)return 0;
    init=initial->expression;e=body->expression;
    if(!init||init->kind!=EX_ASSIGN||init->op||init->left->kind!=EX_OBJECT||init->left->symbol!=index||
       !integer_constant(init->right,&first)||first>=end||end-first>UNROLL_FULL_LIMIT||
       !(((step->kind==EX_PRE||step->kind==EX_POST)&&step->op==TOK_INC)||
         (step->kind==EX_ASSIGN&&step->op=='+'&&integer_constant(step->right,&a)&&a==1))||
       step->left->kind!=EX_OBJECT||step->left->symbol!=index||!e||e->kind!=EX_ASSIGN||e->op||
       width(e->type)!=1||e->type.is_bool||volatile_expression(e))return 0;
    rhs=byte_loop_bits(e->right);
    if(width(rhs->type)!=1||!indexed_operand(e->left,&to)||!indexed_operand(rhs,&from)||
       to.scale!=1||from.scale!=1||!retained_affine_for(to.index,index,&a,&b)||a!=1||
       !retained_affine_for(from.index,index,&c,&d)||c!=1)return 0;
    count=end-first;destination=to.offset+b+first;source=from.offset+d+first;
    if(count<2||destination>65535||source>65535||
       destination+count>width(to.base->type)||source+count>width(from.base->type)||
       (to.base==from.base&&destination<source+count&&source<destination+count))return 0;
    code("; widened fixed byte copy: %u bytes\n",count);to.base->used=from.base->used=1;
    for(i=0;i+1<count;i+=2)
        code("    lda a:.loword(_%s+$%04X)\n    sta a:.loword(_%s+$%04X)\n",from.base->asm_name,source+i,to.base->asm_name,destination+i);
    if(i<count)code("    sep #$20\n.a8\n    lda a:.loword(_%s+$%04X)\n    sta a:.loword(_%s+$%04X)\n    rep #$20\n.a16\n",
                    from.base->asm_name,source+i,to.base->asm_name,destination+i);
    if(loop_observed_outside(cg.function->body,s,index)){code("    lda #$%04X\n",end&65535);store_symbol(index);strength_sync(index,NULL);}
    cg.divmod_available=0;return 1;
}
