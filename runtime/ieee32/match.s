; Same entry as the static C match: s and word are padded four-byte far
; pointers at 3/7,S; A returns a signed word length or zero on mismatch
; Native A16/X16, D=0. Y/D/DBR are preserved; A/X/flags and scratch offsets 0-7 are clobbered
; The C int counter's defined matching-length domain is 0..32767
.setcpu "65816"
.importzp __dp_scratch
.a16
.i16
.export _decimal__match
.segment "CODE"
_decimal__match:
    phy
    lda 5,s
    sta z:__dp_scratch
    lda 7,s
    sta z:__dp_scratch+2
    lda 9,s
    sta z:__dp_scratch+4
    lda 11,s
    sta z:__dp_scratch+6
    ldy #0
    sep #$20
.a8
@next:
    lda [__dp_scratch+4],y
    beq @matched
    sta z:__dp_scratch+3                  ; Unused fourth source-pointer byte
    lda [__dp_scratch],y
    cmp #$41
    bcc @compare
    cmp #$5B
    bcs @compare
    ora #$20                   ; Exactly the runtime's ASCII tolower mapping
@compare:
    cmp z:__dp_scratch+3
    bne @different
    iny
    bra @next
@different:
    rep #$20
.a16
    lda #0
    ply
    rts
@matched:
    rep #$20
.a16
    tya
    ply
    rts
__size_decimal__match = * - _decimal__match
