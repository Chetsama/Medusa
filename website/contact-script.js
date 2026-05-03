// Contact form functionality
document.getElementById('contact-form').addEventListener('submit', function(e) {
  e.preventDefault();

  // Get form values
  const name = document.getElementById('name').value;
  const email = document.getElementById('email').value;
  const message = document.getElementById('message').value;

  // In a real application, you would send this data to a server
  console.log('Form submitted:', { name, email, message });

  // Show success message
  alert('Thank you for your message! I will get back to you soon.');

  // Reset form
  this.reset();
});