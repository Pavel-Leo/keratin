$(document).ready(function () {
  var $nav = $('#main-nav');

  $('.res-nav_click').on('click', function () {
    var expanded = $(this).attr('aria-expanded') === 'true';
    $(this).attr('aria-expanded', String(!expanded));
    $(this).attr('aria-label', expanded ? 'Открыть меню' : 'Закрыть меню');
    $('.main-nav').slideToggle();
    return false;
  });

  // Плавная прокрутка только для якорей, ведущих на текущую страницу.
  $('a[href^="#"]').not('[href="#"]').on('click', function (event) {
    var $target = $($(this).attr('href'));
    if (!$target.length) {
      return;
    }
    event.preventDefault();
    var duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 900;
    $('html, body').stop().animate({
      scrollTop: $target.offset().top - $nav.outerHeight() + 1
    }, duration, 'easeInOutExpo');
    if ($(window).width() < 768) {
      $('.main-nav').hide();
      $('.res-nav_click').attr('aria-expanded', 'false').attr('aria-label', 'Открыть меню');
    }
  });
});

new WOW({
  animateClass: 'animated',
  offset: 100
}).init();
