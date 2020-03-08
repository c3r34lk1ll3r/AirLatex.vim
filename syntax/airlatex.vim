syn match AirLatexTitle #^\s\w\+\n\s=\+#
exec 'syn match AirLatexProjLine #^\s' . escape(g:AirLatexArrowClosed, '~') . '.*#'
exec 'syn match AirLatexProjLine #^\s' . escape(g:AirLatexArrowOpen, '~') . '.*#'

exec 'syn match AirLatexFolderLine   #^\s\s\s\+' . escape(g:AirLatexArrowClosed, '~') . '#'
exec 'syn match AirLatexFolderLine   #^\s\s\s\+' . escape(g:AirLatexArrowOpen, '~') . '#'
syn match AirLatexFile           #^\s\s\s\+.\+\.\w\+#
syn match AirLatexFileRef        #^\s\s\s\s\+-\s.\+\.\w\+#

syn match AirLatexProjInfoLine   #^\s\s\s-\+#
syn match AirLatexProjInfoML     #^\s\s\s\+.\+:\n#
syn match AirLatexProjInfo       #^\s\s\s.\+:\s.\+#
syn match AirLatexProjInfoVal    #:\s\zs.\+# containedin=AirLatexProjInfo

syn match AirLatexStatus         #^\s.\+\s:\s.\+#
syn match AirLatexStatusValue    #:\zs.\+# contained containedin=AirLatexStatus
syn match AirLatexStatusOnline   #Online# contained containedin=AirLatexStatusValue
syn match AirLatexStatusOffline  #Offline# contained containedin=AirLatexStatusValue

syn match AirLatexMenuEntry  #press \[\w\]#


hi def link AirLatexTitle Title
hi def link AirLatexProjLine Special

hi def link AirLatexFolderLine Special
hi def link AirLatexFile Normal
hi def link AirLatexFileRef Comment

hi def link AirLatexProjInfoLine Comment
hi def link AirLatexProjInfo Comment
hi def link AirLatexProjInfoML Comment
hi def link AirLatexProjInfoVal Type

hi def link AirLatexStatus Function
hi def link AirLatexStatusOnline String
hi def link AirLatexStatusOffline Todo
hi def link AirLatexStatusValue Number

hi def link AirLatexMenuEntry Title
