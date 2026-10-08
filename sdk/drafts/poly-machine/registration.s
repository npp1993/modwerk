#NO_APP
	.file	"vector.c"
	.text
	.align	2
	.type	signed_track, @function
signed_track:
	move.l %d2,-(%sp)
	move.l 12(%sp),%d0
	mov3q.l #7,%d1
	cmp.l %d0,%d1
	jcs .L4
	move.l 8(%sp),%a0
	mvz.b 34(%a0,%d0.l),%d1
	subq.l #1,%d1
	tst.l %d1
	jeq .L7
.L4:
	move.l (%sp)+,%d2
	clr.l %d0
	rts
.L7:
	mulu.w #30,%d0
	moveq #80,%d1
	lea 60(%a0,%d0.l),%a0
	mvz.b (%a0),%d0
	cmp.l %d0,%d1
	jne .L4
	mvz.b 1(%a0),%d0
	moveq #76,%d2
	cmp.l %d0,%d2
	jne .L4
	move.b 2(%a0),%d0
	mov3q.l #1,%d1
	move.l (%sp)+,%d2
	eor.l %d1,%d0
	tst.b %d0
	seq %d0
	mvs.b %d0,%d0
	neg.l %d0
	rts
	.size	signed_track, .-signed_track
	.align	2
	.type	retire.part.0, @function
retire.part.0:
	move.l %d2,-(%sp)
	move.l 8(%sp),%d0
	subq.l #8,%d0
	lea poly_extra_track,%a1
	mov3q.l #7,%d2
	mvz.b (%a1,%d0.l),%d1
	cmp.l %d1,%d2
	jcs .L9
	move.l 8(%sp),%d1
	mov3q.l #1,%d2
	subq.l #7,%d1
	lsl.l %d1,%d2
	mvz.b (%a1,%d0.l),%d1
	lea poly_extra_mask,%a1
	not.l %d2
	and.l %d2,(%a1,%d1.l*4)
.L9:
	mvz.w #168,%d1
	clr.b %d2
	lea poly_extra_voices,%a0
	muls.l %d0,%d1
	move.b %d2,(%a0,%d1.l)
	st %d1
	lea poly_extra_note,%a0
	move.b %d1,(%a0,%d0.l)
	move.l (%sp)+,%d2
	rts
	.size	retire.part.0, .-retire.part.0
	.align	2
	.globl	pm_selected
	.type	pm_selected, @function
pm_selected:
	move.l 1187521622,%d0
	add.l #-1073741824,%d0
	move.l %d2,-(%sp)
	cmp.l #133169151,%d0
	jhi .L15
	tst.b -2147483627.l
	jeq .L18
.L15:
	move.l (%sp)+,%d2
	clr.l %d0
	rts
.L18:
	move.b 269161676,%d1
	move.l 1187521622,%a0
	mov3q.l #3,%d2
	move.b 269161679,%d0
	add.l #585088,%a0
	mvz.b %d1,%d1
	and.l %d2,%d0
	move.l %d1,-(%sp)
	mvz.w #6322,%d1
	muls.l %d1,%d0
	pea (%a0,%d0.l)
	jsr signed_track
	addq.l #8,%sp
	move.l (%sp)+,%d2
	rts
	.size	pm_selected, .-pm_selected
	.align	2
	.type	pool_context, @function
pool_context:
	move.l pool_bank,%d0
	cmp.l 1187521622.l,%d0
	jeq .L25
.L21:
	clr.l %d0
	rts
.L25:
	move.b 269161679,%d0
	mov3q.l #3,%d1
	and.l %d1,%d0
	cmp.l pool_part.l,%d0
	jne .L21
	mvz.b 269161676,%d0
	cmp.l pool_track.l,%d0
	jne .L21
	jra pm_selected
	.size	pool_context, .-pool_context
	.align	2
	.globl	pm_type
	.type	pm_type, @function
pm_type:
	move.l 1187521622,%d0
	add.l #-1073741824,%d0
	move.l %d2,-(%sp)
	cmp.l #133169151,%d0
	jhi .L28
	move.l 1187521622,%d0
	mov3q.l #3,%d2
	move.b 269161679,%d1
	add.l #585088,%d0
	move.l 12(%sp),%a0
	lea (-34,%a0),%a0
	and.l %d2,%d1
	mvz.w #6322,%d2
	muls.l %d2,%d1
	mov3q.l #7,%d2
	add.l %d1,%d0
	move.l %a0,%d1
	sub.l %d0,%d1
	cmp.l %d1,%d2
	jcc .L35
.L28:
	move.l 8(%sp),%d0
	move.l (%sp)+,%d2
	rts
.L35:
	mov3q.l #1,%d2
	cmp.l 8(%sp),%d2
	jcs .L28
	move.l %d1,-(%sp)
	move.l %d0,-(%sp)
	jsr signed_track
	addq.l #8,%sp
	tst.l %d0
	jeq .L28
	mov3q.l #5,8(%sp)
	move.l 8(%sp),%d0
	move.l (%sp)+,%d2
	rts
	.size	pm_type, .-pm_type
	.align	2
	.globl	pm_chooser_type
	.type	pm_chooser_type, @function
pm_chooser_type:
	move.l %d3,-(%sp)
	move.l %d2,-(%sp)
	tst.l pool_direct
	jeq .L40
	jsr pool_context
	tst.l %d0
	jne .L50
.L40:
	move.l 1187521622,%d0
	add.l #-1073741824,%d0
	cmp.l #133169151,%d0
	jhi .L43
	move.l 1187521622,%d1
	mov3q.l #3,%d3
	move.b 269161679,%d0
	add.l #585088,%d1
	move.w %d0,%a0
	move.l 16(%sp),%d0
	add.l #-34,%d0
	move.l %a0,%d2
	and.l %d3,%d2
	mvz.w #6322,%d3
	muls.l %d3,%d2
	add.l %d2,%d1
	sub.l %d1,%d0
	mov3q.l #7,%d2
	cmp.l %d0,%d2
	jcc .L51
.L43:
	move.l 12(%sp),%d0
	move.l (%sp)+,%d2
	move.l (%sp)+,%d3
	rts
.L51:
	mov3q.l #1,%d3
	cmp.l 12(%sp),%d3
	jcs .L43
	move.l %d0,-(%sp)
	move.l %d1,-(%sp)
	jsr signed_track
	addq.l #8,%sp
	tst.l %d0
	jeq .L43
	move.l (%sp)+,%d2
	mov3q.l #5,%d0
	move.l (%sp)+,%d3
	rts
.L50:
	move.l 1187521622,%d0
	mov3q.l #3,%d2
	move.b 269161679,%d1
	mvz.w #6322,%d3
	move.l pool_track,%a0
	add.l #585088,%d0
	lea (34,%a0),%a0
	and.l %d2,%d1
	muls.l %d3,%d1
	add.l %d1,%d0
	add.l %a0,%d0
	cmp.l 16(%sp),%d0
	jne .L40
	move.l (%sp)+,%d2
	move.l pool_browse,%d0
	move.l (%sp)+,%d3
	rts
	.size	pm_chooser_type, .-pm_chooser_type
	.align	2
	.globl	pm_assign
	.type	pm_assign, @function
pm_assign:
	lea (-36,%sp),%sp
	move.l 1187521622,%d0
	add.l #-1073741824,%d0
	movem.l #1036,(%sp)
	cmp.l #133169151,%d0
	jhi .L53
	mov3q.l #7,%d0
	cmp.l 44(%sp),%d0
	jcs .L53
	move.l 40(%sp),%d0
	mvz.w #6322,%d3
	sub.l 1187521622,%d0
	move.l %d0,%d1
	add.l #-585088,%d1
	move.l %d1,20(%sp)
	move.l %d1,%d2
	remu.l %d3,%d1:%d2
	tst.l %d1
	jne .L53
	move.l 20(%sp),%d2
	cmp.l #25287,%d2
	jhi .L53
	move.l 44(%sp),%d2
	moveq #30,%d3
	move.l %d0,%a0
	add.l #268525902,%a0
	move.l %a0,32(%sp)
	muls.l %d3,%d2
	move.l %d2,24(%sp)
	tst.l pool_direct
	jne .L74
.L56:
	tst.l 48(%sp)
	jeq .L75
	move.l 40(%sp),%a0
	lea (34,%a0),%a0
	move.l %a0,28(%sp)
.L61:
	cmp.l 44(%sp),%d1
	jeq .L59
	move.l %d1,-(%sp)
	move.l 44(%sp),-(%sp)
	move.l %d1,22(%sp)
	jsr signed_track
	addq.l #8,%sp
	move.l 14(%sp),%d1
	tst.l %d0
	jne .L60
	move.l 28(%sp),%a1
	mvz.b (%a1,%d1.l),%d0
	subq.l #5,%d0
	tst.l %d0
	jeq .L60
.L59:
	addq.l #1,%d1
	moveq #8,%d3
	cmp.l %d1,%d3
	jne .L61
	move.l 24(%sp),%a1
	move.l 40(%sp),%a0
	move.l 40(%sp),%a2
	move.l 24(%sp),%d2
	move.l %d2,%d0
	lea 60(%a0,%a1.l),%a0
	lea 61(%a2,%a1.l),%a1
	add.l #478,%d0
	move.l %a0,%d1
	lea 62(%a2,%d2.l),%a0
	clr.b %d2
	move.l %d1,%a2
	move.b #80,(%a2)
	move.l 32(%sp),%a2
	move.b #76,(%a1)
	move.b #1,(%a0)
	move.b %d2,(%a2,%d0.l)
	move.l 40(%sp),%a2
	move.b %d2,(%a2,%d0.l)
	move.l 32(%sp),%a2
	move.l 24(%sp),%d0
	add.l #484,%d0
	move.b %d2,(%a2,%d0.l)
	move.l 40(%sp),%a2
	move.b %d2,(%a2,%d0.l)
	move.l %d1,%a2
	move.b (%a2),28(%sp)
	move.b (%a1),%d1
	move.b (%a0),%d0
	move.l 32(%sp),%a0
	move.l 24(%sp),%a1
	move.b 28(%sp),%d2
	move.b %d2,60(%a0,%a1.l)
	move.b %d1,61(%a0,%a1.l)
	move.b %d0,62(%a0,%a1.l)
	mov3q.l #1,%d0
	cmp.l 48(%sp),%d0
	jne .L53
	mvz.w #6322,%d3
	move.l 20(%sp),%d1
	clr.b %d2
	move.l 24(%sp),%a0
	divu.l %d3,%d1
	move.l 32(%sp),%a1
	move.l 40(%sp),%a2
	lea (480,%a0),%a0
	move.b %d2,(%a1,%a0.l)
	move.b %d2,(%a2,%a0.l)
	move.l #1187521622,%a0
	mov3q.l #1,%d0
	movem.l (%sp),#1036
	move.l (%a0),pool_bank
	move.l %d1,pool_part
	move.l 44(%sp),%d1
	mov3q.l #1,pool_pending
	move.l %d1,pool_track
	lea (36,%sp),%sp
	rts
.L75:
	move.l 44(%sp),-(%sp)
	move.l 44(%sp),-(%sp)
	jsr signed_track
	move.l 32(%sp),%a2
	move.l 48(%sp),%a1
	move.l 32(%sp),%d2
	lea 62(%a1,%a2.l),%a0
	lea 61(%a1,%a2.l),%a1
	move.l 48(%sp),%a2
	addq.l #8,%sp
	lea 60(%a2,%d2.l),%a2
	move.l %a2,%d1
	tst.l %d0
	jeq .L63
	clr.b (%a0)
	clr.b (%a1)
	clr.b (%a2)
.L63:
	move.l %d1,%a2
	move.b (%a2),19(%sp)
	move.b (%a1),%d1
	move.b (%a0),%d0
	move.l 32(%sp),%a0
	move.l 24(%sp),%a1
	move.b 19(%sp),%d2
	move.b %d2,60(%a0,%a1.l)
	move.b %d1,61(%a0,%a1.l)
	move.b %d0,62(%a0,%a1.l)
.L53:
	movem.l (%sp),#1036
	mov3q.l #1,%d0
	lea (36,%sp),%sp
	rts
.L74:
	move.l %d1,14(%sp)
	jsr pool_context
	move.l 14(%sp),%d1
	tst.l %d0
	jeq .L56
	move.l 1187521622,%d0
	add.l #585088,%d0
	move.b 269161679,%d2
	move.w %d2,%a0
	mov3q.l #3,%d2
	move.l %a0,%d3
	and.l %d2,%d3
	mvz.w #6322,%d2
	muls.l %d2,%d3
	add.l %d3,%d0
	cmp.l 40(%sp),%d0
	jne .L56
	move.l 44(%sp),%d3
	cmp.l pool_track.l,%d3
	jne .L56
	move.l 40(%sp),%a0
	mov3q.l #2,48(%sp)
	lea (34,%a0),%a0
	move.l %a0,28(%sp)
	jra .L61
.L60:
	movem.l (%sp),#1036
	mov3q.l #-1,%d0
	mov3q.l #1,limit_pending
	lea (36,%sp),%sp
	rts
	.size	pm_assign, .-pm_assign
	.align	2
	.globl	pm_pool_choice_draw
	.type	pm_pool_choice_draw, @function
pm_pool_choice_draw:
	clr.l %d0
	rts
	.size	pm_pool_choice_draw, .-pm_pool_choice_draw
	.align	2
	.globl	pm_pool_choice_open
	.type	pm_pool_choice_open, @function
pm_pool_choice_open:
	subq.l #4,%sp
	move.l %a2,-(%sp)
	move.l 1187521622,%d0
	add.l #-1073741824,%d0
	move.l %d2,-(%sp)
	cmp.l #133169151,%d0
	jhi .L78
	tst.b -2147483627.l
	jeq .L85
.L78:
	move.l (%sp)+,%d2
	move.l (%sp)+,%a2
	addq.l #4,%sp
	rts
.L85:
	move.l #269161676,%a1
	mov3q.l #3,%d2
	move.b (%a1),%d1
	move.l 1187521622,%a0
	move.l #269161679,%a2
	move.b (%a2),%d0
	add.l #585088,%a0
	mvz.b %d1,%d1
	and.l %d2,%d0
	move.l %d1,-(%sp)
	mvz.w #6322,%d1
	muls.l %d1,%d0
	pea (%a0,%d0.l)
	move.l %a1,16(%sp)
	jsr signed_track
	addq.l #8,%sp
	move.l 8(%sp),%a1
	tst.l %d0
	jeq .L78
	tst.l 1175346736
	jne .L78
	tst.l 1175351520
	jne .L78
	move.l #1187521622,%a0
	mov3q.l #3,%d1
	move.l (%a0),pool_bank
	move.b (%a2),%d0
	and.l %d0,%d1
	move.l %d1,pool_part
	mvz.b (%a1),%d0
	clr.l pool_pending
	mov3q.l #1,pool_browse
	mov3q.l #1,pool_direct
	move.l %d0,pool_track
	jsr pm_stock_pool_open
	mov3q.l #-1,-(%sp)
	jsr 1074059592
	addq.l #4,%sp
	move.l (%sp)+,%d2
	mov3q.l #1,1187497772
	move.l (%sp)+,%a2
	addq.l #4,%sp
	rts
	.size	pm_pool_choice_open, .-pm_pool_choice_open
	.align	2
	.globl	pm_pool_left
	.type	pm_pool_left, @function
pm_pool_left:
	move.l 4(%sp),%d0
	move.l 8(%sp),%d1
	tst.l 1175351520
	jeq .L86
	clr.l pool_direct
	move.l %d1,8(%sp)
	move.l %d0,4(%sp)
	jmp 1074235708
.L86:
	rts
	.size	pm_pool_left, .-pm_pool_left
	.align	2
	.globl	pm_pool_right
	.type	pm_pool_right, @function
pm_pool_right:
	subq.l #8,%sp
	move.l 12(%sp),%d1
	move.l 16(%sp),%a0
	tst.l 1175351520
	jeq .L91
	tst.l 1175352218
	jne .L91
	mov3q.l #5,%d0
	cmp.l 1175352206.l,%d0
	jeq .L100
.L91:
	move.l %a0,16(%sp)
	move.l %d1,12(%sp)
	addq.l #8,%sp
	jmp 1074237596
.L100:
	move.l %d1,4(%sp)
	move.l %a0,(%sp)
	jsr pm_selected
	move.l 4(%sp),%d1
	move.l (%sp),%a0
	tst.l %d0
	jeq .L91
	jsr 1074235876
	addq.l #8,%sp
	jra pm_pool_choice_open
	.size	pm_pool_right, .-pm_pool_right
	.section	.rodata.str1.1,"aMS",@progbits,1
.LC0:
	.string	"ONE POLY PER PART"
	.text
	.align	2
	.globl	pm_ui_tick
	.type	pm_ui_tick, @function
pm_ui_tick:
	lea (-32,%sp),%sp
	move.l 1187521622,%d0
	add.l #-1073741824,%d0
	movem.l #7196,(%sp)
	cmp.l #133169151,%d0
	jhi .L101
	tst.l limit_pending
	jeq .L103
	clr.l -(%sp)
	pea .LC0
	clr.l limit_pending
	jsr 1074111160
	addq.l #8,%sp
.L103:
	mov3q.l #3,%d1
	mvz.w #6322,%d4
	move.b 269161679,%d2
	move.l 1187521622,%a2
	add.l #585088,%a2
	move.b 269161679,%d0
	clr.l %d3
	and.l %d2,%d1
	mov3q.l #3,%d2
	and.l %d2,%d0
	move.l %d4,%d2
	move.l %d1,28(%sp)
	muls.l %d4,%d1
	muls.l %d0,%d2
	move.l %d1,%d0
	add.l #269111050,%d0
	add.l %d2,%a2
	sub.l %a2,%d1
	move.l %d1,%a0
	add.l #269110990,%a0
	move.l %a0,24(%sp)
	move.l %a2,%d2
	add.l #42,%d2
	lea (34,%a2),%a0
	lea (60,%a2),%a1
.L105:
	mvz.b (%a0),%d1
	subq.l #5,%d1
	tst.l %d1
	jeq .L125
	addq.l #1,%a0
	add.l #30,%d0
	lea (30,%a1),%a1
	cmp.l %a0,%d2
	jne .L105
.L128:
	tst.l %d3
	jne .L126
	tst.l pool_direct
	jeq .L107
.L131:
	tst.l 1175351520
	jne .L108
	clr.l pool_direct
.L107:
	tst.l pool_pending
	jne .L127
.L110:
	mvz.b 269161676,%d0
	mov3q.l #7,%d4
	cmp.l %d0,%d4
	jcs .L113
.L130:
	tst.b 34(%a2,%d0.l)
	jne .L113
	move.l #1074606108,%d0
	move.l %d0,1074618188
.L101:
	movem.l (%sp),#7196
	lea (32,%sp),%sp
	rts
.L125:
	move.l %d0,%a3
	move.l %a1,%a4
	move.b #80,(%a3)+
	move.b #80,(%a4)+
	moveq #1,%d1
	mov3q.l #1,%d3
	lea (30,%a1),%a1
	move.b #76,(%a3)
	move.b #76,(%a4)
	move.l %d0,%a3
	add.l #30,%d0
	move.l 24(%sp),%a4
	move.b %d1,2(%a3)
	move.b %d1,-28(%a1)
	move.b %d1,(%a4,%a0.l)
	clr.b %d1
	move.b #1,(%a0)
	addq.l #1,%a0
	move.b %d1,418(%a3)
	move.b %d1,388(%a1)
	move.b %d1,424(%a3)
	move.b %d1,394(%a1)
	cmp.l %a0,%d2
	jne .L105
	jra .L128
.L113:
	move.l #1074606510,%d0
	move.l %d0,1074618188
	jra .L101
.L127:
	jsr pool_context
	tst.l %d0
	jeq .L129
	tst.l 1175346736
	jne .L110
	tst.l 1175351520
	jne .L110
	jsr pm_pool_choice_open
	mvz.b 269161676,%d0
	mov3q.l #7,%d4
	cmp.l %d0,%d4
	jcs .L113
	jra .L130
.L126:
	move.l 28(%sp),%d2
	mov3q.l #1,%d0
	move.l 1187521622,%a0
	add.l #610376,%a0
	move.b (%a0),%d1
	lsl.l %d2,%d0
	or.l %d0,%d1
	move.b %d1,(%a0)
	move.b 269161566,%d1
	or.l %d1,%d0
	move.b %d0,269161566
	move.l 1187521622,%a0
	add.l #635698,%a0
	mov3q.l #1,(%a0)
	mov3q.l #1,269452696
	jsr 1073905152
	tst.l pool_direct
	jeq .L107
	jra .L131
.L129:
	clr.l pool_pending
	mvz.b 269161676,%d0
	mov3q.l #7,%d4
	cmp.l %d0,%d4
	jcs .L113
	jra .L130
.L108:
	jsr pool_context
	tst.l %d0
	jne .L107
	clr.l pool_direct
	jra .L107
	.size	pm_ui_tick, .-pm_ui_tick
	.align	2
	.globl	pm_is_poly_track
	.type	pm_is_poly_track, @function
pm_is_poly_track:
	mov3q.l #7,%d0
	cmp.l 4(%sp),%d0
	jcs .L135
	move.l 1187521622,%d0
	add.l #-1073741824,%d0
	cmp.l #133169151,%d0
	jls .L139
.L135:
	clr.l %d0
	rts
.L139:
	move.l 1187521622,%a0
	mov3q.l #3,%d1
	move.b 269161679,%d0
	move.l 4(%sp),-(%sp)
	add.l #585088,%a0
	and.l %d1,%d0
	mvz.w #6322,%d1
	muls.l %d1,%d0
	pea (%a0,%d0.l)
	jsr signed_track
	addq.l #8,%sp
	tst.l %d0
	jne .L136
	move.l 1187521622,%a0
	mov3q.l #3,%d1
	move.b 269161679,%d0
	move.l 4(%sp),%a1
	add.l #585088,%a0
	and.l %d1,%d0
	mvz.w #6322,%d1
	muls.l %d1,%d0
	mov3q.l #5,%d1
	add.l %d0,%a0
	move.b 34(%a1,%a0.l),%d0
	eor.l %d1,%d0
	tst.b %d0
	seq %d0
	mvs.b %d0,%d0
	neg.l %d0
	rts
.L136:
	mov3q.l #1,%d0
	rts
	.size	pm_is_poly_track, .-pm_is_poly_track
	.align	2
	.type	admit, @function
admit:
	lea (-52,%sp),%sp
	movem.l #31996,(%sp)
	lea poly_extra_track,%a6
	clr.l %d2
	lea extra_age-32,%a2
	clr.l %d5
	move.l #-2147464744,%d7
	sub.l %a4,%a4
	clr.l 44(%sp)
	clr.l 48(%sp)
	clr.l %d4
	lea poly_extra_voices,%a3
	lea pm_is_poly_track,%a5
.L157:
	mov3q.l #7,%d0
	cmp.l %d2,%d0
	jcc .L177
.L141:
	mvz.w #168,%d0
	move.l %d2,%d6
	subq.l #8,%d6
	move.b (%a6,%d6.l),%d3
	muls.l %d6,%d0
	tst.b (%a3,%d0.l)
	jeq .L147
	mvz.b %d3,%d3
	mov3q.l #7,%d0
	cmp.l %d3,%d0
	jcs .L150
	move.l %d3,-(%sp)
	jsr (%a5)
	addq.l #4,%sp
	tst.l %d0
	jeq .L150
	lea poly_extra_shift,%a0
	mvs.b (%a0,%d6.l),%d6
	lea poly_env_stage,%a1
	move.b (%a1,%d2.l),%d0
	move.l (%a2),%d1
	move.l serial,%a0
	sub.l %d1,%a0
	mov3q.l #3,%d1
	eor.l %d1,%d0
	tst.b %d0
	seq %d0
	mvs.b %d0,%d0
	neg.l %d0
	tst.l %d4
	jeq .L166
.L179:
	cmp.l %d0,%d5
	jcs .L164
	jeq .L178
	move.l 44(%sp),%a0
	move.l %d5,%d0
.L151:
	lea poly_track_inc,%a1
	moveq #26,%d5
	move.l (%a1,%d3.l*4),%d1
	move.l %d1,%d3
	lsr.l %d5,%d3
	addq.l #1,%d4
	and.l #67108863,%d1
	move.l %d3,%d5
	tst.l %d1
	sne %d1
	mvs.b %d1,%d1
	sub.l %d1,%d5
	cmp.l %d3,%d1
	jne .L152
	mov3q.l #1,%d5
.L152:
	tst.l %d6
	jle .L153
	add.l #11,%d6
	moveq #59,%d1
	cmp.l %d6,%d1
	jcs .L167
	moveq #12,%d3
	divu.l %d3,%d6
	lsl.l %d6,%d5
.L153:
	moveq #32,%d1
	cmp.l %d5,%d1
	jcs .L167
	lea 1(%a4,%d5.l),%a4
	move.l %a0,44(%sp)
	move.l %d0,%d5
.L147:
	addq.l #1,%d2
	moveq #39,%d3
	cmp.l %d2,%d3
	jeq .L156
.L174:
	add.l #168,%d7
	addq.l #4,%a2
.L180:
	mov3q.l #7,%d0
	cmp.l %d2,%d0
	jcs .L141
.L177:
	move.l %d7,%a0
	tst.b (%a0)
	jeq .L144
	move.l %d2,-(%sp)
	jsr (%a5)
	addq.l #4,%sp
	tst.l %d0
	jeq .L144
	lea poly_primary_shift,%a0
	mvs.b (%a0,%d2.l),%d6
	lea poly_env_stage,%a1
	move.b (%a1,%d2.l),%d0
	lea primary_age,%a0
	move.l (%a0,%d2.l*4),%d1
	move.l serial,%a0
	sub.l %d1,%a0
	mov3q.l #3,%d1
	move.l %d2,%d3
	eor.l %d1,%d0
	tst.b %d0
	seq %d0
	mvs.b %d0,%d0
	neg.l %d0
	tst.l %d4
	jne .L179
.L166:
	move.l %d2,48(%sp)
	jra .L151
.L167:
	moveq #32,%d5
	lea 1(%a4,%d5.l),%a4
	move.l %a0,44(%sp)
	move.l %d0,%d5
	jra .L147
.L156:
	tst.l %d4
	jeq .L140
	add.l 56(%sp),%d4
	moveq #8,%d5
	cmp.l %d4,%d5
	jcs .L159
	move.l 60(%sp),%d0
	moveq #40,%d1
	add.l %a4,%d0
	cmp.l %d0,%d1
	jcc .L140
.L159:
	mov3q.l #7,%d3
	cmp.l 48(%sp),%d3
	jcs .L160
	move.w 50(%sp),%d0
	st %d5
	move.l 48(%sp),%a1
	clr.l %d2
	lea extra_age-32,%a2
	sub.l %a4,%a4
	move.l #-2147464744,%d7
	clr.l %d4
	clr.l 44(%sp)
	clr.l 48(%sp)
	lea poly_extra_voices,%a3
	lea pm_is_poly_track,%a5
	mulu.w #168,%d0
	move.l %d0,%a0
	add.l #-2147464744,%a0
	clr.b (%a0)
	lea poly_primary_note,%a0
	move.b %d5,(%a0,%a1.l)
	clr.l %d5
	jra .L157
.L140:
	movem.l (%sp),#31996
	lea (52,%sp),%sp
	rts
.L150:
	move.l %d2,-(%sp)
	moveq #39,%d3
	jsr (retire.part.0)
	addq.l #4,%sp
	addq.l #1,%d2
	cmp.l %d2,%d3
	jne .L174
	jra .L156
.L144:
	addq.l #1,%d2
	add.l #168,%d7
	addq.l #4,%a2
	jra .L180
.L164:
	move.l %d2,48(%sp)
	mov3q.l #1,%d0
	jra .L151
.L178:
	cmp.l 44(%sp),%a0
	jhi .L166
	move.l 44(%sp),%a0
	jra .L151
.L160:
	move.l 48(%sp),-(%sp)
	jsr (retire.part.0)
	addq.l #4,%sp
	lea extra_age-32,%a2
	clr.l %d2
	move.l #-2147464744,%d7
	clr.l %d5
	clr.l 44(%sp)
	clr.l 48(%sp)
	sub.l %a4,%a4
	clr.l %d4
	lea poly_extra_voices,%a3
	lea pm_is_poly_track,%a5
	jra .L157
	.size	admit, .-admit
	.align	2
	.globl	pm_clear_extensions
	.type	pm_clear_extensions, @function
pm_clear_extensions:
	lea (-12,%sp),%sp
	mov3q.l #7,%d0
	movem.l #1036,(%sp)
	move.l 16(%sp),%d2
	cmp.l %d2,%d0
	jcs .L181
	lea dirty,%a0
	tst.b (%a0,%d2.l)
	jeq .L181
	clr.l %d0
	lea poly_extra_track,%a0
	lea poly_extra_voices,%a2
	lea poly_extra_note,%a1
.L184:
	mvz.b (%a0,%d0.l),%d1
	cmp.l %d1,%d2
	jeq .L190
	addq.l #1,%d0
	moveq #31,%d3
	cmp.l %d0,%d3
	jne .L184
.L191:
	st %d1
	move.l %d2,%d0
	sub.l %a0,%a0
	lsl.l #6,%d0
	lea poly_extra_mask,%a1
	clr.l (%a1,%d2.l*4)
	lea poly_primary_note,%a1
	move.b %d1,(%a1,%d2.l)
	move.l %d0,%a1
	add.l #poly_held,%a1
.L185:
	st %d3
	moveq #64,%d0
	move.b %d3,(%a1,%a0.l)
	addq.l #1,%a0
	cmp.l %a0,%d0
	jne .L185
	clr.b %d1
	lea poly_chord_count,%a0
	move.b %d1,(%a0,%d2.l)
	lea poly_pending_key,%a0
	move.b %d3,(%a0,%d2.l)
	lea poly_armed_key,%a0
	move.b %d3,(%a0,%d2.l)
	lea poly_released,%a0
	move.b %d1,(%a0,%d2.l)
	lea dirty,%a0
	move.b %d1,(%a0,%d2.l)
.L181:
	movem.l (%sp),#1036
	lea (12,%sp),%sp
	rts
.L190:
	mvz.w #168,%d1
	clr.b %d3
	muls.l %d0,%d1
	move.b %d3,(%a2,%d1.l)
	st %d1
	moveq #31,%d3
	move.b %d1,(%a0,%d0.l)
	move.b %d1,(%a1,%d0.l)
	addq.l #1,%d0
	cmp.l %d0,%d3
	jne .L184
	jra .L191
	.size	pm_clear_extensions, .-pm_clear_extensions
	.align	2
	.globl	pm_enforce_budget
	.type	pm_enforce_budget, @function
pm_enforce_budget:
	move.l 4(%sp),%d0
	mov3q.l #7,%d1
	cmp.l %d0,%d1
	jcs .L192
	lea poly_track_inc,%a1
	move.l (%a1,%d0.l*4),%d1
	lea budget_tuning,%a0
	cmp.l (%a0,%d0.l*4),%d1
	jeq .L192
	lea (%a1,%d0.l*4),%a1
	move.l (%a1),(%a0,%d0.l*4)
	clr.l -(%sp)
	clr.l -(%sp)
	jsr admit
	addq.l #8,%sp
.L192:
	rts
	.size	pm_enforce_budget, .-pm_enforce_budget
	.align	2
	.globl	pm_reserve
	.type	pm_reserve, @function
pm_reserve:
	lea (-36,%sp),%sp
	mov3q.l #7,%d0
	movem.l #3196,(%sp)
	move.l 40(%sp),%d3
	cmp.l %d3,%d0
	jcs .L207
	lea poly_pending_shift,%a0
	moveq #26,%d5
	move.b (%a0,%d3.l),%d2
	lea poly_track_inc,%a0
	move.l (%a0,%d3.l*4),%d0
	move.l %d0,%d1
	lsr.l %d5,%d1
	move.l serial,%d4
	addq.l #1,%d4
	and.l #67108863,%d0
	move.l %d4,serial
	move.l %d1,%a0
	tst.l %d0
	sne %d0
	mvs.b %d0,%d0
	sub.l %d0,%d1
	cmp.l %a0,%d0
	jeq .L217
.L198:
	tst.b %d2
	jle .L199
	mvs.b %d2,%d2
	moveq #59,%d6
	add.l #11,%d2
	cmp.l %d2,%d6
	jcs .L208
	moveq #12,%d5
	divu.l %d5,%d2
	lsl.l %d2,%d1
.L199:
	moveq #32,%d6
	cmp.l %d1,%d6
	jcs .L218
	addq.l #1,%d1
.L200:
	move.l %d1,-(%sp)
	mov3q.l #1,-(%sp)
	jsr admit
	mvz.w #168,%d0
	addq.l #8,%sp
	muls.l %d3,%d0
	move.l %d0,%a0
	add.l #-2147464744,%a0
	tst.b (%a0)
	jeq .L202
.L220:
	clr.l %d0
	lea poly_extra_voices,%a0
.L206:
	mvz.w #168,%d2
	move.l %d0,%d1
	muls.l %d0,%d2
	addq.l #1,%d0
	tst.b (%a0,%d2.l)
	jeq .L219
	moveq #31,%d1
	cmp.l %d0,%d1
	jne .L206
.L202:
	moveq #1,%d2
	lea primary_age,%a0
	mov3q.l #-1,%d0
	move.l %d4,(%a0,%d3.l*4)
	lea dirty,%a0
	move.b %d2,(%a0,%d3.l)
.L196:
	movem.l (%sp),#3196
	lea (36,%sp),%sp
	rts
.L217:
	mov3q.l #1,%d1
	jra .L198
.L218:
	moveq #32,%d1
	addq.l #1,%d1
	jra .L200
.L208:
	moveq #33,%d1
	move.l %d1,-(%sp)
	mov3q.l #1,-(%sp)
	jsr admit
	mvz.w #168,%d0
	addq.l #8,%sp
	muls.l %d3,%d0
	move.l %d0,%a0
	add.l #-2147464744,%a0
	tst.b (%a0)
	jeq .L202
	jra .L220
.L219:
	lea poly_extra_track,%a0
	mov3q.l #7,%d5
	mvz.b (%a0,%d1.l),%d2
	move.l %d2,%a1
	mov3q.l #1,%d2
	lsl.l %d0,%d2
	move.l %d1,%d0
	cmp.l %a1,%d5
	jcs .L221
	mvz.b (%a0,%d1.l),%d6
	lea poly_extra_mask,%a1
	move.l %d2,%d5
	not.l %d5
	lea extra_age,%a2
	and.l %d5,(%a1,%d6.l*4)
	move.b %d3,(%a0,%d1.l)
	lea primary_age,%a0
	lea (%a0,%d3.l*4),%a3
	move.l %d6,28(%sp)
	or.l %d2,(%a1,%d3.l*4)
	move.l (%a3),(%a2,%d1.l*4)
.L222:
	moveq #1,%d2
	move.l %d4,(%a0,%d3.l*4)
	lea dirty,%a0
	move.b %d2,(%a0,%d3.l)
	jra .L196
.L221:
	move.b %d3,(%a0,%d1.l)
	lea primary_age,%a0
	lea (%a0,%d3.l*4),%a3
	lea extra_age,%a2
	lea poly_extra_mask,%a1
	or.l %d2,(%a1,%d3.l*4)
	move.l (%a3),(%a2,%d1.l*4)
	jra .L222
.L207:
	movem.l (%sp),#3196
	mov3q.l #-1,%d0
	lea (36,%sp),%sp
	rts
	.size	pm_reserve, .-pm_reserve
	.align	2
	.globl	pm_release_head
	.type	pm_release_head, @function
pm_release_head:
	lea (-12,%sp),%sp
	mov3q.l #7,%d0
	move.l 16(%sp),%a0
	movem.l #3076,(%sp)
	move.l 20(%sp),%d2
	cmp.l %a0,%d0
	jcs .L223
	lea poly_primary_note,%a1
	mvz.b (%a1,%a0.l),%d0
	cmp.l %d0,%d2
	jeq .L237
.L225:
	clr.l %d0
	lea poly_extra_track,%a1
	lea poly_extra_note,%a2
	lea poly_env_stage,%a3
.L227:
	mvz.b (%a1,%d0.l),%d1
	cmp.l %d1,%a0
	jeq .L238
.L226:
	addq.l #1,%d0
	moveq #31,%d1
	cmp.l %d0,%d1
	jne .L227
.L223:
	movem.l (%sp),#3076
	lea (12,%sp),%sp
	rts
.L238:
	mvz.b (%a2,%d0.l),%d1
	cmp.l %d1,%d2
	jne .L226
	st %d1
	move.b %d1,(%a2,%d0.l)
	tst.b 8(%a3,%d0.l)
	jeq .L226
	moveq #3,%d1
	move.b %d1,8(%a3,%d0.l)
	addq.l #1,%d0
	moveq #31,%d1
	cmp.l %d0,%d1
	jne .L227
	jra .L223
.L237:
	st %d1
	move.b %d1,(%a1,%a0.l)
	lea poly_env_stage,%a1
	tst.b (%a1,%a0.l)
	jeq .L225
	moveq #3,%d0
	lea poly_extra_note,%a2
	lea poly_env_stage,%a3
	move.b %d0,(%a1,%a0.l)
	clr.l %d0
	lea poly_extra_track,%a1
	jra .L227
	.size	pm_release_head, .-pm_release_head
	.align	2
	.globl	pm_record_key
	.type	pm_record_key, @function
pm_record_key:
	lea (-24,%sp),%sp
	mov3q.l #7,%d0
	movem.l #124,(%sp)
	cmp.l 28(%sp),%d0
	jcs .L239
	moveq #124,%d4
	cmp.l 32(%sp),%d4
	jcs .L239
	tst.l 1175263018
	jeq .L239
	move.l 28(%sp),%d5
	sub.l %a0,%a0
	lea poly_held,%a1
	clr.l %d1
	moveq #125,%d2
	lsl.l #6,%d5
	add.l %d5,%a1
.L243:
	mvz.b (%a1,%a0.l),%d0
	moveq #124,%d6
	addq.l #1,%a0
	cmp.l %d0,%d6
	jcs .L241
	cmp.l %d2,%d0
	jcc .L242
	move.l %d0,%d2
.L242:
	addq.l #1,%d1
.L241:
	moveq #64,%d0
	cmp.l %a0,%d0
	jne .L243
	subq.l #1,%d1
	mov3q.l #3,%d4
	cmp.l %d1,%d4
	jcs .L239
	clr.w %d4
	lea poly_held,%a1
	sub.l %a0,%a0
	add.l %d5,%a1
.L245:
	mvz.b (%a1,%a0.l),%d0
	mov3q.l #1,%d3
	addq.l #1,%a0
	moveq #124,%d6
	move.l %d0,%d1
	sub.l %d2,%d1
	lsl.l %d1,%d3
	cmp.l %d0,%d6
	jcs .L244
	moveq #11,%d0
	cmp.l %d1,%d0
	jcs .L239
	or.l %d3,%d4
.L244:
	moveq #64,%d6
	cmp.l %a0,%d6
	jne .L245
	mvz.w %d4,%d4
	lea chord_masks,%a0
	clr.l %d3
.L247:
	mvz.w (%a0),%d0
	addq.l #2,%a0
	cmp.l %d4,%d0
	jeq .L246
	addq.l #1,%d3
	cmp.l #232,%d3
	jne .L247
.L239:
	movem.l (%sp),#124
	lea (24,%sp),%sp
	rts
.L246:
	move.l 1187506518,%d5
	tst.l 1187503398
	jeq .L258
	move.l #1074013980,%a0
.L249:
	move.l %d5,-(%sp)
	move.l 32(%sp),-(%sp)
	jsr (%a0)
	addq.l #8,%sp
	move.l %d0,%d4
	moveq #63,%d0
	cmp.l %d4,%d0
	jcs .L239
	move.l %d5,-(%sp)
	move.l #1074012504,%a0
	move.l %d4,-(%sp)
	move.l %d2,-(%sp)
	clr.l -(%sp)
	move.l 44(%sp),-(%sp)
	move.l %a0,40(%sp)
	jsr (%a0)
	move.l %d5,-(%sp)
	move.l %d4,-(%sp)
	move.l %d3,-(%sp)
	pea 30.w
	move.l 64(%sp),-(%sp)
	move.l 60(%sp),%a0
	jsr (%a0)
	lea (40,%sp),%sp
	movem.l (%sp),#124
	lea (24,%sp),%sp
	rts
.L258:
	move.l #1074015516,%a0
	jra .L249
	.size	pm_record_key, .-pm_record_key
	.align	2
	.globl	pm_sequence_stage
	.type	pm_sequence_stage, @function
pm_sequence_stage:
	subq.l #8,%sp
	move.l %a2,-(%sp)
	move.l %d2,-(%sp)
	mov3q.l #7,%d0
	cmp.l 20(%sp),%d0
	jcc .L275
.L259:
	move.l (%sp)+,%d2
	move.l (%sp)+,%a2
	addq.l #8,%sp
	rts
.L275:
	move.l 20(%sp),-(%sp)
	jsr pm_is_poly_track
	addq.l #4,%sp
	tst.l %d0
	jeq .L259
	clr.b %d0
	move.l 24(%sp),%a0
	move.l 20(%sp),%d2
	lea sequence_count,%a1
	mvz.b (%a0),%d1
	lea sequence_index,%a0
	move.b %d0,(%a0,%d2.l)
	move.l 24(%sp),%a0
	move.b %d0,(%a1,%d2.l)
	moveq #124,%d2
	move.b 30(%a0),%d0
	cmp.l %d1,%d2
	jcs .L259
	mvz.b %d0,%d0
	move.l %d0,%a0
	cmp.l #231,%d0
	jhi .L259
	st %d0
	move.l 24(%sp),%a2
	move.l 32(%sp),%d2
	move.b #-1,(%a2)
	move.b %d0,30(%a2)
	clr.b %d0
	move.l 28(%sp),%a2
	clr.b (%a2)
	move.b %d0,30(%a2)
	btst #0,%d2
	jeq .L259
	move.l 20(%sp),%d2
	clr.l %d0
	lea chord_masks,%a2
	lsl.l #2,%d2
	move.l %d2,12(%sp)
	mvz.w (%a2,%a0.l*2),%d2
	move.l 12(%sp),%a2
	add.l #sequence_notes,%a2
	sub.l %a0,%a0
	move.l %a2,12(%sp)
	move.l %d2,8(%sp)
.L262:
	move.l 8(%sp),%d2
	btst %d0,%d2
	jeq .L261
	moveq #124,%d2
	cmp.l %d1,%d2
	jcs .L259
	move.l 12(%sp),%a2
	move.b %d1,(%a2,%a0.l)
	addq.l #1,%a0
.L261:
	addq.l #1,%d0
	addq.l #1,%d1
	moveq #12,%d2
	cmp.l %d0,%d2
	jne .L262
	move.w %a0,%d0
	move.l 20(%sp),%d1
	move.b %d0,(%a1,%d1.l)
	move.l (%sp)+,%d2
	move.l (%sp)+,%a2
	addq.l #8,%sp
	rts
	.size	pm_sequence_stage, .-pm_sequence_stage
	.align	2
	.globl	pm_sequence_next
	.type	pm_sequence_next, @function
pm_sequence_next:
	move.l %a2,-(%sp)
	move.l %d2,-(%sp)
	move.l 12(%sp),%d0
	mov3q.l #7,%d1
	cmp.l %d0,%d1
	jcs .L277
	lea poly_pending_key,%a0
	mvz.b (%a0,%d0.l),%d1
	cmp.l #255,%d1
	jne .L283
	lea sequence_index,%a2
	move.b (%a2,%d0.l),%d1
	lea sequence_count,%a0
	mvz.b (%a0,%d0.l),%d2
	move.l %d2,%a0
	mvz.b %d1,%d2
	move.l %d2,%a1
	cmp.l %d2,%a0
	jls .L277
	move.l %d0,%d2
	addq.l #1,%d1
	lsl.l #2,%d2
	move.b %d1,(%a2,%d0.l)
	move.l %d2,%a0
	add.l #sequence_notes,%a0
	move.l (%sp)+,%d2
	mvz.b (%a0,%a1.l),%d0
	move.l (%sp)+,%a2
	rts
.L283:
	clr.b %d2
	lea sequence_count,%a0
	move.b %d2,(%a0,%d0.l)
.L277:
	move.l (%sp)+,%d2
	mov3q.l #-1,%d0
	move.l (%sp)+,%a2
	rts
	.size	pm_sequence_next, .-pm_sequence_next
	.data
	.type	sequence_index, @object
	.size	sequence_index, 8
sequence_index:
	.zero	8
	.type	sequence_count, @object
	.size	sequence_count, 8
sequence_count:
	.zero	8
	.type	sequence_notes, @object
	.size	sequence_notes, 32
sequence_notes:
	.zero	32
	.section	.rodata
	.align	2
	.type	chord_masks, @object
	.size	chord_masks, 464
chord_masks:
	.word	1
	.word	3
	.word	5
	.word	9
	.word	17
	.word	33
	.word	65
	.word	129
	.word	257
	.word	513
	.word	1025
	.word	2049
	.word	7
	.word	11
	.word	19
	.word	35
	.word	67
	.word	131
	.word	259
	.word	515
	.word	1027
	.word	2051
	.word	13
	.word	21
	.word	37
	.word	69
	.word	133
	.word	261
	.word	517
	.word	1029
	.word	2053
	.word	25
	.word	41
	.word	73
	.word	137
	.word	265
	.word	521
	.word	1033
	.word	2057
	.word	49
	.word	81
	.word	145
	.word	273
	.word	529
	.word	1041
	.word	2065
	.word	97
	.word	161
	.word	289
	.word	545
	.word	1057
	.word	2081
	.word	193
	.word	321
	.word	577
	.word	1089
	.word	2113
	.word	385
	.word	641
	.word	1153
	.word	2177
	.word	769
	.word	1281
	.word	2305
	.word	1537
	.word	2561
	.word	3073
	.word	15
	.word	23
	.word	39
	.word	71
	.word	135
	.word	263
	.word	519
	.word	1031
	.word	2055
	.word	27
	.word	43
	.word	75
	.word	139
	.word	267
	.word	523
	.word	1035
	.word	2059
	.word	51
	.word	83
	.word	147
	.word	275
	.word	531
	.word	1043
	.word	2067
	.word	99
	.word	163
	.word	291
	.word	547
	.word	1059
	.word	2083
	.word	195
	.word	323
	.word	579
	.word	1091
	.word	2115
	.word	387
	.word	643
	.word	1155
	.word	2179
	.word	771
	.word	1283
	.word	2307
	.word	1539
	.word	2563
	.word	3075
	.word	29
	.word	45
	.word	77
	.word	141
	.word	269
	.word	525
	.word	1037
	.word	2061
	.word	53
	.word	85
	.word	149
	.word	277
	.word	533
	.word	1045
	.word	2069
	.word	101
	.word	165
	.word	293
	.word	549
	.word	1061
	.word	2085
	.word	197
	.word	325
	.word	581
	.word	1093
	.word	2117
	.word	389
	.word	645
	.word	1157
	.word	2181
	.word	773
	.word	1285
	.word	2309
	.word	1541
	.word	2565
	.word	3077
	.word	57
	.word	89
	.word	153
	.word	281
	.word	537
	.word	1049
	.word	2073
	.word	105
	.word	169
	.word	297
	.word	553
	.word	1065
	.word	2089
	.word	201
	.word	329
	.word	585
	.word	1097
	.word	2121
	.word	393
	.word	649
	.word	1161
	.word	2185
	.word	777
	.word	1289
	.word	2313
	.word	1545
	.word	2569
	.word	3081
	.word	113
	.word	177
	.word	305
	.word	561
	.word	1073
	.word	2097
	.word	209
	.word	337
	.word	593
	.word	1105
	.word	2129
	.word	401
	.word	657
	.word	1169
	.word	2193
	.word	785
	.word	1297
	.word	2321
	.word	1553
	.word	2577
	.word	3089
	.word	225
	.word	353
	.word	609
	.word	1121
	.word	2145
	.word	417
	.word	673
	.word	1185
	.word	2209
	.word	801
	.word	1313
	.word	2337
	.word	1569
	.word	2593
	.word	3105
	.word	449
	.word	705
	.word	1217
	.word	2241
	.word	833
	.word	1345
	.word	2369
	.word	1601
	.word	2625
	.word	3137
	.word	897
	.word	1409
	.word	2433
	.word	1665
	.word	2689
	.word	3201
	.word	1793
	.word	2817
	.word	3329
	.word	3585
	.globl	poly_extra_mask
	.data
	.align	2
	.type	poly_extra_mask, @object
	.size	poly_extra_mask, 32
poly_extra_mask:
	.zero	32
	.type	dirty, @object
	.size	dirty, 8
dirty:
	.zero	8
	.align	2
	.type	serial, @object
	.size	serial, 4
serial:
	.zero	4
	.align	2
	.type	extra_age, @object
	.size	extra_age, 124
extra_age:
	.zero	124
	.align	2
	.type	primary_age, @object
	.size	primary_age, 32
primary_age:
	.zero	32
	.align	2
	.type	budget_tuning, @object
	.size	budget_tuning, 32
budget_tuning:
	.zero	32
	.align	2
	.type	limit_pending, @object
	.size	limit_pending, 4
limit_pending:
	.zero	4
	.align	2
	.type	pool_browse, @object
	.size	pool_browse, 4
pool_browse:
	.zero	4
	.align	2
	.type	pool_direct, @object
	.size	pool_direct, 4
pool_direct:
	.zero	4
	.align	2
	.type	pool_pending, @object
	.size	pool_pending, 4
pool_pending:
	.zero	4
	.align	2
	.type	pool_track, @object
	.size	pool_track, 4
pool_track:
	.zero	4
	.align	2
	.type	pool_part, @object
	.size	pool_part, 4
pool_part:
	.zero	4
	.align	2
	.type	pool_bank, @object
	.size	pool_bank, 4
pool_bank:
	.zero	4

#APP
/* Original POLY integration; registration seams adapted from octabam's */
/* MIT Analog BD machine.s (Sam Banks / repeat98). Replayed stock instructions */
/* are generated only in the private local build by prepare.py. */
        .text
        .global pm_machine_name, pm_src_names, pm_main_commit
        .global pm_src_commit, pm_src_commit2, pm_name_a, pm_name_b
        .global pm_setup_open, pm_chooser_open, pm_setup_row, pm_chooser_row
        .global pm_setup_edit6, pm_setup_draw6, pm_tick_hook
        .equ BANK_PTR, 0x46c82456
        .equ PART_OFF, 0x8ed80
pm_machine_name:
        move.l 4(%sp),%d0
        cmpi.l #5,%d0
        beq.s 1f
        jmp pm_name_replay
1:      lea pm_name(%pc),%a0
        move.l %a0,%d0
        rts
pm_src_names:
        .long 0x400b3eac,0x400b3e98,0x400b7c67,0x400b5413,0x400b7a63,pm_name
pm_row_type:
        lea -20(%sp),%sp
        movem.l %d1/%a0-%a1,8(%sp)
        move.l %d0,(%sp)
        move.l %a0,4(%sp)
        jsr pm_type
        movem.l 8(%sp),%d1/%a0-%a1
        lea 20(%sp),%sp
        rts
pm_main_commit:
        lea -32(%sp),%sp
        movem.l %d0-%d2/%a0-%a1,12(%sp)
        move.l %a1,%d2
        add.l %d0,%d2
        addi.l #PART_OFF,%d2
        move.l %d2,(%sp)
        move.l %d1,4(%sp)
        moveq #0,%d2
        cmpi.l #5,%d4
        bne.s 1f
        moveq #1,%d2
1:      move.l %d2,8(%sp)
        jsr pm_assign
        tst.l %d0
        bmi.s .main_refuse
        cmpi.l #5,%d4
        bne.s 2f
        move.l %d0,%d4
2:      movem.l 12(%sp),%d0-%d2/%a0-%a1
        lea 32(%sp),%sp
        jmp pm_main_replay
.main_refuse:
        movem.l 12(%sp),%d0-%d2/%a0-%a1
        lea 32(%sp),%sp
        jmp 0x4007989c
pm_src_commit:
        pea 0x4005a61c
        bra.s pm_src_common
pm_src_commit2:
        pea 0x4005a856
pm_src_common:
        move.l 0x460d5c30,%d1
        lea -32(%sp),%sp
        movem.l %d0/%d2-%d3/%a0-%a1,12(%sp)
        move.l %a1,%d3
        add.l %d0,%d3
        addi.l #PART_OFF,%d3
        move.l %d3,(%sp)
        move.l %d2,4(%sp)
        moveq #0,%d3
        cmpi.l #5,%d1
        bne.s 1f
        moveq #1,%d3
1:      move.l %d3,8(%sp)
        move.l %d1,%d3
        jsr pm_assign
        tst.l %d0
        bmi.s .src_refuse
        cmpi.l #5,%d3
        beq.s 2f
        move.l %d3,%d0
2:      move.l %d0,%d1
        movem.l 12(%sp),%d0/%d2-%d3/%a0-%a1
        lea 32(%sp),%sp
        rts
.src_refuse:
        movem.l 12(%sp),%d0/%d2-%d3/%a0-%a1
        lea 32(%sp),%sp
        mvz.b (%a0),%d1
        move.l %d1,0x460d5c30
        rts
pm_setup_open:
        move.b (%a0),%d3
        move.l %d0,-(%sp)
        mvs.b %d3,%d0
        bsr pm_row_type
        move.l %d0,%d3
        move.l (%sp)+,%d0
        mvs.b %d3,%d4
        pea 0x400bb704
        jmp 0x400585e6
pm_chooser_open:
        mvs.b (%a0),%d0
        bsr pm_chooser_row_type
        move.l %d0,-(%sp)
        pea 0x460e7386
        jmp 0x40078890
pm_name_a:
        bsr pm_name_pick
        jmp 0x4003d722
pm_name_b:
        bsr pm_name_pick
        jmp 0x4004c374
pm_name_pick:
        bsr pm_row_type
        lea pm_src_names(%pc),%a0
        move.l (%a0,%d0.l*4),%d1
        rts
pm_setup_row:
        mvs.b (%a0),%d0
        lea 24(%sp),%sp
        bsr pm_row_type
        jmp 0x4003c986
pm_chooser_row:
        mvs.b (%a0),%d0
        bsr pm_chooser_row_type
        cmp.l %d0,%d2
        bne.s 1f
        jmp 0x400786ce
1:      jmp 0x400786fc
pm_chooser_row_type:
        lea -20(%sp),%sp
        movem.l %d1/%a0-%a1,8(%sp)
        move.l %d0,(%sp)
        move.l %a0,4(%sp)
        jsr pm_chooser_type
        movem.l 8(%sp),%d1/%a0-%a1
        lea 20(%sp),%sp
        rts
/* SRC SETUP on row five edits the real underlying pool's settings. */
pm_pool_kind:
        move.l %a0,-(%sp)
        move.l %d1,-(%sp)
        movea.l BANK_PTR,%a0
        mvz.b 0x100b14cf,%d1
        mulu.w #6322,%d1
        adda.l %d1,%a0
        mvz.b 0x100b14cc,%d1
        adda.l #0x8eda2,%a0
        mvz.b (%a0,%d1.l),%d0
        move.l (%sp)+,%d1
        move.l (%sp)+,%a0
        rts
pm_setup_edit6:
        cmpi.l #5,%d2
        bne.s 1f
        move.l %a3,%d0
        cmpi.l #4,%d0
        bne.s 2f
        jmp 0x4003a624
2:      bsr pm_pool_kind
        move.l %d0,%d2
1:      jmp pm_edit_replay
pm_setup_draw6:
        cmpi.l #5,%d6
        bne.s 1f
        move.l %d0,-(%sp)
        bsr pm_pool_kind
        move.l %d0,%d6
        move.l (%sp)+,%d0
1:      jmp pm_draw_replay
pm_tick_hook:
        jsr 0x4005213c
        jsr 0x4007e940
        jsr pm_ui_tick
        jmp 0x40052228
pm_name:
        .asciz "POLY"
        .balign 2
/* POLY browser entry delegates directly to the stock FLEX sample pool. */
        .global pm_pool_open, pm_stock_pool_open, pm_lipm_draw, pm_pool_title
pm_pool_open:
        lea -16(%sp),%sp
        movem.l %d0-%d1/%a0-%a1,(%sp)
        jsr pm_selected
        tst.l %d0
        beq.s .pool_stock
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea 16(%sp),%sp
        jmp pm_pool_choice_open
.pool_stock:
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea 16(%sp),%sp
pm_stock_pool_open:
        move.l %a2,-(%sp)
        tst.l 0x460e70e0
        jmp 0x400791ec
pm_lipm_draw:
        lea -16(%sp),%sp
        movem.l %d0-%d1/%a0-%a1,(%sp)
        jsr pm_pool_choice_draw
        tst.l %d0
        beq.s .lipm_stock
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea 16(%sp),%sp
        rts
.lipm_stock:
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea 16(%sp),%sp
        lea -24(%sp),%sp
        movem.l %d2-%d3/%a2-%a5,(%sp)
        jmp 0x4006d78c
pm_pool_title:
        moveq #1,%d6
        cmpi.l #5,%d0
        bne.s .title_stock
        lea -16(%sp),%sp
        movem.l %d0-%d1/%a0-%a1,(%sp)
        jsr pm_selected
        tst.l %d0
        beq.s .title_unsigned
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea 16(%sp),%sp
        bra.s .title_pool
.title_unsigned:
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea 16(%sp),%sp
.title_stock:
        cmp.l %d0,%d6
        bcs.s .title_plain
.title_pool:
        jmp 0x40077b62
.title_plain:
        jmp 0x40077b70

/* After native step-lock publication. Preserve every live caller register. */
.global pm_sequence_publish
pm_sequence_publish:
        lea -16(%sp),%sp
        movem.l %d0-%d1/%a0-%a1,(%sp)
        move.l 114(%sp),-(%sp)     | original sp+98: trigger command
        move.l %a3,-(%sp)          | published lock masks
        move.l %a2,-(%sp)          | published lock values
        move.l 142(%sp),-(%sp)     | original sp+114: track (16+12)
        jsr pm_sequence_stage
        lea 16(%sp),%sp
        movem.l (%sp),%d0-%d1/%a0-%a1
        lea 16(%sp),%sp
        movea.l 180(%sp),%a1      | displaced instruction
        adda.l #0x80000110,%a1
        jmp 0x4000bb18

.text
.balign 2
pm_name_replay:
.space 6
jmp 0x400334de
pm_main_replay:
.space 6
jmp 0x40079822
pm_edit_replay:
.space 8
jmp 0x4003a536
pm_draw_replay:
.space 8
jmp 0x4003cda0
