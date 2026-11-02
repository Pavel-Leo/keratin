from django.contrib.admin import AdminSite


class StudioAdminSite(AdminSite):
    """Админка со входом по логину и паролю."""

    site_header = "Keratin studio"
    site_title = "Keratin studio"
    index_title = "Управление сайтом"
