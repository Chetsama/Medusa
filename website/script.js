// Complete carousel implementation with indicator functionality
let currentSlide = 0;

// Wait for DOM to be ready
document.addEventListener("DOMContentLoaded", function () {
  initializeCarousel();
});

function initializeCarousel() {
  // Get all carousel elements
  const slides = document.querySelectorAll(".carousel-item");
  const prevButton = document.querySelector(".carousel-control.prev");
  const nextButton = document.querySelector(".carousel-control.next");
  const indicators = document.querySelectorAll(".indicator");

  // Validate we have the required elements
  if (slides.length === 0) {
    console.error("Carousel: ERROR - No slides found");
    return;
  }

  if (!prevButton || !nextButton) {
    console.error("Carousel: ERROR - Navigation buttons not found");
    return;
  }

  // Setup initial state
  slides[0].classList.add("active");
  if (indicators.length > 0) {
    indicators[0].classList.add("active");
  }

  // Setup event listeners for navigation buttons
  prevButton.addEventListener("click", function (e) {
    e.preventDefault();
    changeSlide(-1);
  });

  nextButton.addEventListener("click", function (e) {
    e.preventDefault();
    changeSlide(1);
  });

  // Setup event listeners for indicators
  indicators.forEach((indicator, index) => {
    indicator.addEventListener("click", function (e) {
      e.preventDefault();
      goToSlide(index);
    });
  });

  // Setup auto-advance
  setInterval(() => {
    changeSlide(1);
  }, 7500);
}

function changeSlide(direction) {
  const slides = document.querySelectorAll(".carousel-item");
  const indicators = document.querySelectorAll(".indicator");

  if (slides.length === 0) {
    console.error("Carousel: ERROR - No slides to change");
    return;
  }

  // Remove active class from current slide and indicator
  slides[currentSlide].classList.remove("active");
  if (indicators.length > 0) {
    indicators[currentSlide].classList.remove("active");
  }

  // Calculate new slide index
  if (direction === 1) {
    currentSlide = (currentSlide + 1) % slides.length;
  } else {
    currentSlide = (currentSlide - 1 + slides.length) % slides.length;
  }

  // Add active class to new slide and indicator
  slides[currentSlide].classList.add("active");
  if (indicators.length > 0) {
    indicators[currentSlide].classList.add("active");
  }
}

function goToSlide(index) {
  const slides = document.querySelectorAll(".carousel-item");
  const indicators = document.querySelectorAll(".indicator");

  if (slides.length === 0) {
    console.error("Carousel: ERROR - No slides to change");
    return;
  }

  // Remove active class from current slide and indicator
  slides[currentSlide].classList.remove("active");
  if (indicators.length > 0) {
    indicators[currentSlide].classList.remove("active");
  }

  // Set new current slide
  currentSlide = index;

  // Add active class to new slide and indicator
  slides[currentSlide].classList.add("active");
  if (indicators.length > 0) {
    indicators[currentSlide].classList.add("active");
  }
}
