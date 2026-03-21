# Modern Photo Gallery Website

A responsive, modern photo gallery website built with HTML, CSS, and JavaScript. Features include filtering by category, lightbox functionality, and a clean, attractive design.

## Features

- **Responsive Design**: Works on all device sizes
- **Photo Filtering**: Filter photos by category (Nature, Urban, Portrait, Abstract)
- **Lightbox Gallery**: Click any photo to view it in a larger modal
- **Modern UI**: Clean, attractive design with smooth animations
- **Contact Form**: Built-in contact form for visitors
- **Navigation**: Smooth scrolling navigation with active states

## Files Included

1. `index.html` - Main HTML structure
2. `styles.css` - All styling and responsive design
3. `script.js` - Interactive JavaScript functionality
4. `server.js` - Simple Node.js server to serve the website
5. `package.json` - Project dependencies and metadata

## How to Run

1. Navigate to the photo-gallery directory:
```bash
cd photo-gallery
```

2. Install dependencies (if needed):
```bash
npm install
```

3. Start the server:
```bash
npm start
```

4. Open your browser and navigate to `http://localhost:3000`

## Customization

To customize the photo gallery:

1. **Add More Photos**: Edit `script.js` and add more photo objects to the `photos` array
2. **Change Categories**: Modify the categories in the HTML filter buttons and update the photo data
3. **Modify Styling**: Edit `styles.css` to change colors, fonts, and layout
4. **Update Content**: Modify text in `index.html` to match your preferences

## Photo Data Structure

Each photo object in `script.js` includes:
- `id`: Unique identifier
- `title`: Photo title
- `category`: Category for filtering (nature, urban, portrait, abstract)
- `src`: Image URL
- `description`: Photo description

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

This project is licensed under the MIT License - see the LICENSE file for details.