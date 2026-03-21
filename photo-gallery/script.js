// DOM Elements
const navbar = document.querySelector('.navbar');
const navToggle = document.querySelector('.nav-toggle');
const navMenu = document.querySelector('.nav-menu');
const filterButtons = document.querySelectorAll('.filter-btn');
const galleryGrid = document.getElementById('galleryGrid');
const lightbox = document.getElementById('lightbox');
const lightboxImg = document.getElementById('lightboxImg');
const caption = document.getElementById('caption');
const closeBtn = document.querySelector('.close');
const contactForm = document.getElementById('contactForm');

// Sample photo data - in a real app this would come from a database or API
const photos = [
    {
        id: 1,
        title: "Mountain Sunrise",
        category: "nature",
        src: "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Beautiful sunrise over the mountains"
    },
    {
        id: 2,
        title: "City Life",
        category: "urban",
        src: "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Vibrant urban landscape at dusk"
    },
    {
        id: 3,
        title: "Portrait Session",
        category: "portrait",
        src: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Intimate portrait session"
    },
    {
        id: 4,
        title: "Abstract Colors",
        category: "abstract",
        src: "https://images.unsplash.com/photo-1513364775268-6c140326f90d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Colorful abstract composition"
    },
    {
        id: 5,
        title: "Forest Pathway",
        category: "nature",
        src: "https://images.unsplash.com/photo-1448375240586-882707db888b?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Peaceful forest trail"
    },
    {
        id: 6,
        title: "Urban Architecture",
        category: "urban",
        src: "https://images.unsplash.com/photo-1493246507139-91e8fad9978e?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Modern architectural design"
    },
    {
        id: 7,
        title: "Street Portrait",
        category: "portrait",
        src: "https://images.unsplash.com/photo-1544035100-0a59b0b9a5d7?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Street photography portrait"
    },
    {
        id: 8,
        title: "Geometric Patterns",
        category: "abstract",
        src: "https://images.unsplash.com/photo-1516483638261-f9a4c303f953?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Geometric abstract art"
    },
    {
        id: 9,
        title: "Ocean Waves",
        category: "nature",
        src: "https://images.unsplash.com/photo-1505228395891-9a51e7e86bf6?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Powerful ocean waves at sunset"
    },
    {
        id: 10,
        title: "Night Sky",
        category: "nature",
        src: "https://images.unsplash.com/photo-1462331940025-496dfbfc7564?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Starry night sky over mountains"
    },
    {
        id: 11,
        title: "Modern Cityscape",
        category: "urban",
        src: "https://images.unsplash.com/photo-1477959858617-67f85cf4f1df?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Contemporary city skyline"
    },
    {
        id: 12,
        title: "Candid Moment",
        category: "portrait",
        src: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=600&h=400&q=80",
        description: "Authentic candid portrait"
    }
];

// Initialize the gallery
function initGallery() {
    displayPhotos(photos);
    setupEventListeners();
}

// Display photos in the gallery
function displayPhotos(photosToDisplay) {
    galleryGrid.innerHTML = '';
    
    photosToDisplay.forEach(photo => {
        const galleryItem = document.createElement('div');
        galleryItem.className = 'gallery-item';
        galleryItem.dataset.category = photo.category;
        
        galleryItem.innerHTML = `
            <img src="${photo.src}" alt="${photo.title}">
            <div class="overlay">
                <h3>${photo.title}</h3>
                <p>${photo.description}</p>
            </div>
        `;
        
        galleryGrid.appendChild(galleryItem);
    });
    
    // Add click event to each gallery item
    document.querySelectorAll('.gallery-item').forEach(item => {
        item.addEventListener('click', () => openLightbox(item));
    });
}

// Filter photos by category
function filterPhotos(category) {
    if (category === 'all') {
        displayPhotos(photos);
    } else {
        const filteredPhotos = photos.filter(photo => photo.category === category);
        displayPhotos(filteredPhotos);
    }
    
    // Update active button
    filterButtons.forEach(btn => {
        if (btn.dataset.filter === category) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// Open lightbox with clicked image
function openLightbox(element) {
    const imgSrc = element.querySelector('img').src;
    const imgAlt = element.querySelector('img').alt;
    
    lightboxImg.src = imgSrc;
    caption.textContent = imgAlt;
    lightbox.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

// Close lightbox
function closeLightbox() {
    lightbox.style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Setup event listeners
function setupEventListeners() {
    // Mobile menu toggle
    navToggle.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        navToggle.classList.toggle('active');
    });
    
    // Close mobile menu when clicking a link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            navMenu.classList.remove('active');
            navToggle.classList.remove('active');
        });
    });
    
    // Filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            const category = button.dataset.filter;
            filterPhotos(category);
        });
    });
    
    // Close lightbox
    closeBtn.addEventListener('click', closeLightbox);
    
    // Close lightbox when clicking outside image
    lightbox.addEventListener('click', (e) => {
        if (e.target === lightbox) {
            closeLightbox();
        }
    });
    
    // Handle form submission
    contactForm.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Thank you for your message! We will get back to you soon.');
        contactForm.reset();
    });
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
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
}

// Handle scroll effect for navbar
window.addEventListener('scroll', () => {
    if (window.scrollY > 100) {
        navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.98)';
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
    } else {
        navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
    }
});

// Initialize the gallery when the page loads
document.addEventListener('DOMContentLoaded', initGallery);

// Add keyboard support for lightbox
document.addEventListener('keydown', (e) => {
    if (lightbox.style.display === 'block') {
        if (e.key === 'Escape') {
            closeLightbox();
        }
    }
});