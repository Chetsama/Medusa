// Modern Photo Gallery JavaScript

// Sample photo data - in a real app, this would come from a database or API
const photos = [
    { id: 1, title: "Mountain Landscape", category: "nature", src: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 2, title: "City Skyline", category: "urban", src: "https://images.unsplash.com/photo-1477959858617-03855932450d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 3, title: "Portrait Photography", category: "portrait", src: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 4, title: "Abstract Art", category: "abstract", src: "https://images.unsplash.com/photo-1515405293632-06ff5524852e?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 5, title: "Forest Path", category: "nature", src: "https://images.unsplash.com/photo-1448375240586-882707db888b?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 6, title: "Urban Architecture", category: "urban", src: "https://images.unsplash.com/photo-1497366754035-f200968a6e72?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 7, title: "Street Portrait", category: "portrait", src: "https://images.unsplash.com/photo-1544035100-0a9050192f90?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 8, title: "Colorful Patterns", category: "abstract", src: "https://images.unsplash.com/photo-1515405293632-06ff5524852e?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 9, title: "Ocean Waves", category: "nature", src: "https://images.unsplash.com/photo-1505228395891-9a51e7e86bf6?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 10, title: "Modern Cityscape", category: "urban", src: "https://images.unsplash.com/photo-1477959858617-03855932450d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 11, title: "Close-up Portrait", category: "portrait", src: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" },
    { id: 12, title: "Geometric Patterns", category: "abstract", src: "https://images.unsplash.com/photo-1515405293632-06ff5524852e?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80" }
];

// DOM Elements
const galleryGrid = document.getElementById('galleryGrid');
const filterButtons = document.querySelectorAll('.filter-btn');
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightboxImg');
const lightboxCaption = document.getElementById('lightboxCaption');
const closeBtn = document.querySelector('.close');
const prevBtn = document.querySelector('.prev-btn');
const nextBtn = document.querySelector('.next-btn');
const themeToggle = document.querySelector('.theme-toggle');
const contactForm = document.getElementById('contactForm');

// Current state
let currentCategory = 'all';
let currentPhotoIndex = 0;

// Initialize the gallery
function initGallery() {
    renderGallery(photos);
    setupEventListeners();
}

// Render gallery items
function renderGallery(photoArray) {
    galleryGrid.innerHTML = '';
    
    photoArray.forEach(photo => {
        const galleryItem = document.createElement('div');
        galleryItem.className = 'gallery-item';
        galleryItem.dataset.category = photo.category;
        galleryItem.innerHTML = `
            <img src="${photo.src}" alt="${photo.title}">
        `;
        galleryGrid.appendChild(galleryItem);
        
        // Add click event to open lightbox
        galleryItem.addEventListener('click', () => openLightbox(photoArray, photo.id));
    });
}

// Filter gallery items
function filterGallery(category) {
    currentCategory = category;
    
    // Update active button
    filterButtons.forEach(btn => {
        if (btn.dataset.filter === category) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
    
    // Filter and re-render
    if (category === 'all') {
        renderGallery(photos);
    } else {
        const filteredPhotos = photos.filter(photo => photo.category === category);
        renderGallery(filteredPhotos);
    }
}

// Open lightbox
function openLightbox(photoArray, photoId) {
    const photo = photoArray.find(p => p.id === photoId);
    if (!photo) return;
    
    lightboxImg.src = photo.src;
    lightboxCaption.textContent = photo.title;
    
    // Find index for navigation
    currentPhotoIndex = photoArray.findIndex(p => p.id === photoId);
    
    lightbox.style.display = 'block';
    document.body.style.overflow = 'hidden'; // Prevent scrolling
    
    // Focus on lightbox image for keyboard navigation
    lightboxImg.focus();
}

// Close lightbox
function closeLightbox() {
    lightbox.style.display = 'none';
    document.body.style.overflow = 'auto'; // Re-enable scrolling
}

// Navigation functions
function showPrevPhoto(photoArray) {
    if (currentPhotoIndex > 0) {
        currentPhotoIndex--;
        updateLightbox(photoArray[currentPhotoIndex]);
    }
}

function showNextPhoto(photoArray) {
    if (currentPhotoIndex < photoArray.length - 1) {
        currentPhotoIndex++;
        updateLightbox(photoArray[currentPhotoIndex]);
    }
}

// Update lightbox with new photo
function updateLightbox(photo) {
    lightboxImg.src = photo.src;
    lightboxCaption.textContent = photo.title;
}

// Setup event listeners
function setupEventListeners() {
    // Filter buttons
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterGallery(btn.dataset.filter);
        });
    });
    
    // Lightbox events
    closeBtn.addEventListener('click', closeLightbox);
    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
            closeLightbox();
        }
    });
    
    // Navigation buttons
    prevBtn.addEventListener('click', () => showPrevPhoto(photos));
    nextBtn.addEventListener('click', () => showNextPhoto(photos));
    
    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        if (lightbox.style.display === 'block') {
            if (e.key === 'Escape') {
                closeLightbox();
            } else if (e.key === 'ArrowLeft') {
                showPrevPhoto(photos);
            } else if (e.key === 'ArrowRight') {
                showNextPhoto(photos);
            }
        }
    });
    
    // Theme toggle
    themeToggle.addEventListener('click', toggleTheme);
    
    // Contact form submission
    contactForm.addEventListener('submit', handleFormSubmit);
}

// Toggle dark/light mode
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    
    // Change icon based on theme
    const icon = themeToggle.querySelector('i');
    if (document.body.classList.contains('dark-mode')) {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
    }
}

// Handle form submission
function handleFormSubmit(e) {
    e.preventDefault();
    
    // Get form values
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;
    
    // Simple validation
    if (name && email && message) {
        // In a real application, you would send this to a server
        alert('Thank you for your message! We will get back to you soon.');
        contactForm.reset();
    } else {
        alert('Please fill in all fields.');
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    initGallery();
});

// Add smooth scrolling for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        
        const targetId = this.getAttribute('href');
        if (targetId === '#') return;
        
        const targetElement = document.querySelector(targetId);
        if (targetElement) {
            window.scrollTo({
                top: targetElement.offsetTop - 70,
                behavior: 'smooth'
            });
        }
    });
});