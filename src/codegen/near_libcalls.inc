/* ABI adapters for standard-library calls whose arguments originate as near
 * pointers. Public declarations/symbols and arbitrary far calls are untouched.
 * Unlike a bank-number guess, the fallback preserves far progression even
 * beyond a complete 64-KiB scan. */
static Expr *near_string_argument(Expr *e)
{
    while(e->kind==EX_CAST&&far_pointer(value_type(e->type))&&far_pointer(value_type(e->left->type)))e=e->left;
    if(e->kind!=EX_CAST||!far_pointer(value_type(e->type))||!value_type(e->left->type).pointers||
       far_pointer(value_type(e->left->type))||volatile_expression(e))return NULL;
    return e->left;
}
static void near_strcmp_name(char *name,size_t size)
{
    snprintf(name,size,"__near_strcmp_%s",cg.parser->unit);
}
static void zicc_smul8_name(char *name,size_t size)
{
    snprintf(name,size,"__zicc_smul8_%s",cg.parser->unit);
}
static void zicc_pack_coeff_name(char *name,size_t size)
{
    snprintf(name,size,"__zicc_pack_coeff_%s",cg.parser->unit);
}
static int near_library_call(Expr *e)
{
    Symbol *s=e->symbol;Expr *left,*right;char name[132];
    if(cg.parser->no_strength_reduction||cg.parser->no_body_optimizations||cg.function->symbol->interrupt||
       strcmp(s->name,"strcmp")||s->defined||s->param_count!=2||s->variadic||e->arg_count!=2||
       s->type.pointers||s->type.base!=TY_INT||s->type.is_unsigned||
       s->params[0].base!=TY_CHAR||s->params[1].base!=TY_CHAR||
       s->params[0].pointers!=1||s->params[1].pointers!=1||
       !far_pointer(s->params[0])||!far_pointer(s->params[1])||
       !(left=near_string_argument(e->args[0]))||!(right=near_string_argument(e->args[1])))return 0;
    /* Retain the existing argument evaluation order and evaluate each once */
    load_word_pair(left,right);
    near_strcmp_name(name,sizeof name);call_entry(name);s->used=1;cg.near_strcmp=1;cg.arithmetic=1;
    cg.divmod_available=0;return 1;
}
static void emit_near_library(void)
{
    char name[132];unsigned loop,different,less,equal,done,id;
    const char *ret=cg.parser->long_return?"rtl":"rts";
    if(cg.need_smul8){
        unsigned pos_r=++cg.label,pos_l=++cg.label,pos_sign=++cg.label;
        zicc_smul8_name(name,sizeof name);
        id=++cg.parser->function_count;
        code("; allocation function %u begin\n.segment \"CODE\"\n.export %s\n%s:\n",id,name,name);
        code("    lda z:__arith_rhs\n    eor z:__arith_lhs\n    php\n    lda z:__arith_rhs\n    bpl cg_%s_%u\n    eor #$FFFF\n    inc a\n",cg.parser->unit,pos_r);
        label(pos_r);
        code("    sep #$20\n.a8\n    sta f:$004202\n    rep #$20\n.a16\n    lda z:__arith_lhs\n    bpl cg_%s_%u\n    eor #$FFFF\n    inc a\n",cg.parser->unit,pos_l);
        label(pos_l);
        code("    sep #$20\n.a8\n    sta f:$004203\n    rep #$20\n.a16\n    plp\n    bpl cg_%s_%u\n    lda #$0000\n    sec\n    sbc f:$004216\n    %s\n",cg.parser->unit,pos_sign,ret);
        label(pos_sign);
        code("    lda f:$004216\n    %s\n__size_%s = * - %s\n; allocation function %u end\n",ret,name+1,name,id);
    }
    if(cg.need_pack_coeff){
        unsigned pos=++cg.label;
        zicc_pack_coeff_name(name,sizeof name);
        id=++cg.parser->function_count;
        code("; allocation function %u begin\n.segment \"CODE\"\n.export %s\n%s:\n",id,name,name);
        code("    cmp #$0000\n    bpl cg_%s_%u\n    eor #$FFFF\n    inc a\n    ora #$7F00\n    sta f:$004202\n    %s\n",cg.parser->unit,pos,ret);
        label(pos);
        code("    ora #$8000\n    sta f:$004202\n    %s\n__size_%s = * - %s\n; allocation function %u end\n",ret,name+1,name,id);
    }
    if(!cg.near_strcmp)return;
    near_strcmp_name(name,sizeof name);loop=++cg.label;different=++cg.label;less=++cg.label;equal=++cg.label;done=++cg.label;
    id=++cg.parser->function_count;
    code("; allocation function %u begin\n.segment \"CODE\"\n.export %s\n%s:\n",id,name,name);
    code("; near-origin strcmp: word inputs X/A, public far progression\n    phy\n    stx z:__arith_lhs\n    sta z:__arith_lhs+2\n    ldy #0\n    sep #$20\n.a8\n");
    label(loop);code("    lda (__arith_lhs),y\n    beq cg_%s_%u\n    cmp (__arith_lhs+2),y\n    bne cg_%s_%u\n    iny\n    bne cg_%s_%u\n",cg.parser->unit,equal,cg.parser->unit,different,cg.parser->unit,loop);
    /* (dp),Y carries the effective address into the following bank, just as
     * [far],Y does. On Y wrap both original roots advance by one bank. */
    code("    rep #$20\n.a16\n    pea $007F\n    lda z:__arith_lhs+2\n    pha\n    pea $007F\n    lda z:__arith_lhs\n    pha\n");
    call_entry("_strcmp");code("    tax\n    tsc\n    clc\n    adc #8\n    tcs\n    txa\n");jump(done);
    label(different);code("    bcc cg_%s_%u\n    rep #$20\n.a16\n    lda #1\n",cg.parser->unit,less);jump(done);
    label(less);code("    rep #$20\n.a16\n    lda #$FFFF\n");jump(done);
    label(equal);code("    cmp (__arith_lhs+2),y\n    bne cg_%s_%u\n    rep #$20\n.a16\n    lda #0\n",cg.parser->unit,less);
    label(done);code("    ply\n    rts\n__size_%s = * - %s\n; allocation function %u end\n",name+1,name,id);
}
