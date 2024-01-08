from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from main.forms import ContactUsForm
from main.models import News


def index(request):
    return render(request, 'main/index.html')


def contact_us(request):
    if request.method == "POST":
        contact_form = ContactUsForm(request.POST)
        if contact_form.is_valid():
            contact_form.save()
        messages.success(request, "Your message has been sent Successfully..")
        return redirect(reverse("index"))
    else:
        return render(request, 'main/contact.html')


def about_us(request):
    return render(request, 'main/about.html')


def news(request):
    if 'search' in request.GET:
        keyword = request.GET.get('search')
        news_list: News = News.objects.filter(title__icontains=keyword)
    else:
        news_list: News = News.objects.all()

    most_recent: News = news_list[:2]
    items_per_page: int = 1
    paginator: Paginator = Paginator(news_list, items_per_page)
    page = request.GET.get('page')
    try:
        current_page = paginator.page(page)
    except PageNotAnInteger:
        current_page = paginator.page(1)
    except EmptyPage:
        current_page = paginator.page(paginator.num_pages)

    context = {"current_page": current_page, 'recent_news': most_recent}
    return render(request, 'main/news.html', context)


def news_detail(request, slug):
    news_object: News = get_object_or_404(News, slug=slug)
    return render(request, 'main/news-detail.html', {"news": news_object})
