from django.contrib.auth.decorators import login_required
from annoying.decorators import render_to
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django.views.decorators.cache import never_cache
from simplepagination import paginate
from main.forms import post_forms
from main.models import *
from parser.utils import unparse

@never_cache
@login_required
@render_to('drafts.html')
@paginate(style='digg', per_page=10)
def draft(request):
    drafts = Draft.objects.filter(author=request.user, is_draft=True).order_by('-id')
    return {
        'object_list': drafts
    }

@never_cache
@login_required
def edit_draft(request, id):
    draft = get_object_or_404(Draft, author=request.user, id=id)
    preview = False
    is_draft = False
    if request.POST.get('draft'):
        is_draft = True
    if request.POST.get('preview'):
        preview = True
        is_draft = True
    if draft.type not in (Post.TYPE_ANSWER, Post.TYPE_MULTIPLE_ANSWER):
        form = post_forms[draft.type]
        if request.method == 'POST':
            form = form(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                draft.set_data(data)
                if is_draft:
                    post = draft
                else:
                    post = Post.from_draft(draft)
                post.save(edit=False)
                if not is_draft:
                    post.create_comment_root()
                    post.set_tags(data['tags'])
                    return HttpResponseRedirect('/post/%d/' % (post.id))
            else:
                try:
                    blog = draft.blog.id
                except AttributeError:
                    blog = None
                return render_to_response('newpost.html', {
                    'form': form,
                    'blogs': Blog.create_list(request.user.get_profile(), blog),
                    'type': draft.type,
                    'extend': 'base.html'
                }, context_instance=RequestContext(request))
        else:
            data = {
                'tags': draft.raw_tags,
                'title': draft.title,
                'text': unparse(draft.text),
                'addition':draft.addition
            }
            form = form(data)
            try:
                blog = draft.blog.id
            except AttributeError:
                blog = None
            return render_to_response('newpost.html', {
                'form': form,
                'blogs': Blog.create_list(request.user.get_profile(), blog),
                'preview': utils.parse(draft.text, VALID_TAGS, VALID_ATTRS),
                'type': draft.type,
                'extend': 'base.html',
                'draft': True,
                'id': draft.id
            }, context_instance=RequestContext(request))
    if preview:
        return HttpResponseRedirect('/draft/%d/' %(draft.id))
    else:
        return HttpResponseRedirect('/draft/')

@login_required
def delete_draft(request, id):
    """Remove draft

    Keywords Arguments:
    id -- int -- draft id

    Returns: redirect
    """
    draft = get_object_or_404(
        Draft, id=id,
        author=request.user,
        is_draft=True
    )
    draft.delete()
    return HttpResponseRedirect('/draft/')