from django.shortcuts import render, get_object_or_404

from apps.agency.models import AgencyAbout, News, LeadershipProfile


def public_home(request):
    about = AgencyAbout.get_public()
    news_list = News.objects.filter(is_published=True).order_by("-published_at")[:6]
    return render(request, "public/home.html", {"about": about, "news_list": news_list})


def public_about_detail(request):
    about = AgencyAbout.get_public()
    if not about:
        return render(request, "public/about_empty.html", status=404)

    about.inc_views()  # Счётчик только тут
    return render(request, "public/agency_about_detail.html", {"about": about})


def public_leadership_list(request):
    leaders = (
        LeadershipProfile.objects
        .filter(is_published=True, employee__is_active=True)
        .select_related("employee", "employee__position", "employee__department")
        .order_by("sort_order", "employee__last_name", "employee__first_name")
    )
    return render(request, "public/leadership_list.html", {"leaders": leaders})


def public_news_list(request):
    # только новости
    news_list = News.objects.filter(is_published=True, announcement=False).order_by("-published_at")
    return render(request, "public/news_list.html", {"news_list": news_list})


def public_news_detail(request, pk: int):
    obj = get_object_or_404(News, pk=pk, is_published=True)
    obj.inc_views()
    return render(request, "public/news_detail.html", {"obj": obj})


def public_announcements_list(request):
    # только объявления
    news_list = News.objects.filter(is_published=True, announcement=True).order_by("-published_at")
    return render(request, "public/announcements_list.html", {"news_list": news_list})

