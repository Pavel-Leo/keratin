import pytest

from studio.models import (
    Article,
    ArticleSection,
    PriceCategory,
    PriceItem,
    Service,
)


@pytest.fixture
def service(db):
    return Service.objects.create(
        title="Кератиновое выпрямление",
        menu_title="Кератин",
        slug="keratin",
        teaser="5 причин сделать кератиновое выпрямление.",
        subtitle="Первая строка\nвторая строка",
        body="<ul><li><p>Гладкие и ровные волосы.</p></li></ul>",
    )


@pytest.fixture
def article(db):
    article = Article.objects.create(
        title="Советы по уходу за волосами",
        slug="care-tips",
        teaser="Как продлить эффект процедур.",
    )
    ArticleSection.objects.create(
        article=article,
        heading="Сушите волосы правильно,\nи они скажут вам спасибо!",
        body="<p>Используйте термозащиту.</p>",
    )
    return article


@pytest.fixture
def price(db):
    category = PriceCategory.objects.create(
        title="Кератин/ботокс", note="Адаптивная нанопластика +1500 ₽"
    )
    PriceItem.objects.create(category=category, name="25 см", price=2500)
    PriceItem.objects.create(
        category=category, name="Длинные волосы", price=6500, price_from=True
    )
    return category


@pytest.fixture
def content(service, article, price):
    return {"service": service, "article": article, "price": price}
