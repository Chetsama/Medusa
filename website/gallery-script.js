// Gallery functionality
const galleryGrid = document.querySelector('.gallery-grid');

// Generate placeholder images
const imageCount = 8;
for (let i = 1; i <= imageCount; i++) {
  const imageCard = document.createElement('div');
  imageCard.className = 'image-card';

  const img = document.createElement('img');
  img.src = `images/photo${i}.jpg`;
  img.alt = `Photo ${i}`;

  imageCard.appendChild(img);
  galleryGrid.appendChild(imageCard);
}

// Create overlay element
const overlay = document.createElement('div');
overlay.className = 'image-overlay';
overlay.innerHTML = '<img class="overlay-image" alt="Enlarged image">';
document.body.appendChild(overlay);

// Add click event to all image cards
document.querySelectorAll('.image-card').forEach(card => {
  card.addEventListener('click', function() {
    const imgSrc = this.querySelector('img').src;
    const overlayImage = overlay.querySelector('.overlay-image');

    overlayImage.src = imgSrc;
    overlay.classList.add('active');

    // Close on overlay click
    overlay.addEventListener('click', function(e) {
      if (e.target === overlay) {
        overlay.classList.remove('active');
      }
    });
  });
});