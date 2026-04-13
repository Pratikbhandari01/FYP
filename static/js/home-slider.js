document.addEventListener("DOMContentLoaded", function () {
    const sliderElement = document.querySelector(".hero-slider.swiper");
    if (!sliderElement || typeof Swiper === "undefined") {
        return;
    }

    new Swiper(sliderElement, {
        loop: true,
        speed: 800,
        autoplay: {
            delay: 3500,
            disableOnInteraction: false,
            pauseOnMouseEnter: true,
        },
        navigation: {
            nextEl: ".hero-slider-next",
            prevEl: ".hero-slider-prev",
        },
        pagination: {
            el: ".hero-slider-pagination",
            clickable: true,
        },
    });
});
