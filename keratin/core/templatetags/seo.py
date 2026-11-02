"""Адреса и разметка для поисковиков и превью ссылок в соцсетях."""

import json

from django import template
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

OG_IMAGE = "img/og-image.jpg"
# Внутри <script> нельзя оставлять символы, которые закроют тег.
JSON_ESCAPES = {ord(char): chr(92) + f"u{ord(char):04x}" for char in "<>&"}


@register.simple_tag(takes_context=True)
def canonical_url(context):
    request = context["request"]
    return request.build_absolute_uri(request.path)


@register.simple_tag(takes_context=True)
def absolute_static(context, path):
    return context["request"].build_absolute_uri(static(path))


def business_data(request, contacts):
    data = {
        "@context": "https://schema.org",
        "@type": "HairSalon",
        "name": contacts.name,
        "url": request.build_absolute_uri(reverse("studio:index")),
        "image": request.build_absolute_uri(static(OG_IMAGE)),
    }
    if contacts.phone:
        data["telephone"] = contacts.phone
    if contacts.email:
        data["email"] = contacts.email
    street = ", ".join(
        part for part in [contacts.street, contacts.place] if part
    )
    if street or contacts.city:
        data["address"] = {"@type": "PostalAddress", "addressCountry": "RU"}
        if street:
            data["address"]["streetAddress"] = street
        if contacts.city:
            data["address"]["addressLocality"] = contacts.city
    links = [url for _icon, _title, url in contacts.social_links]
    if links:
        data["sameAs"] = links
    return data


@register.simple_tag(takes_context=True)
def business_json_ld(context):
    """Сведения о салоне по schema.org для карточки в поиске."""
    data = business_data(context["request"], context["contacts"])
    text = json.dumps(data, ensure_ascii=False).translate(JSON_ESCAPES)
    return format_html(
        '<script type="application/ld+json">{}</script>',
        mark_safe(text),  # noqa: S308
    )
