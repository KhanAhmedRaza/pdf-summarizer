// Create placeholder SVG illustrations for the landing page
const fs = require('fs');
const path = require('path');

// Ensure the static/img directory exists
const imgDir = path.join(__dirname, '..', 'static', 'img');
if (!fs.existsSync(imgDir)) {
  fs.mkdirSync(imgDir, { recursive: true });
}

// Create hero illustration SVG
const heroIllustration = `<svg width="600" height="400" xmlns="http://www.w3.org/2000/svg">
  <style>
    .document { fill: #f2f2f2; stroke: #4361ee; stroke-width: 2; }
    .page-content { fill: #e0e0e0; }
    .highlight { fill: #4cc9f0; }
    .arrow { fill: none; stroke: #7209b7; stroke-width: 3; stroke-linecap: round; stroke-linejoin: round; }
    .summary { fill: white; stroke: #4361ee; stroke-width: 2; }
    .summary-line { fill: #e0e0e0; }
    .ai-circle { fill: rgba(114, 9, 183, 0.2); }
    .ai-core { fill: #7209b7; }
  </style>
  
  <!-- Original Document -->
  <rect class="document" x="50" y="50" width="200" height="280" rx="5" />
  <rect class="page-content" x="70" y="80" width="160" height="15" rx="2" />
  <rect class="page-content" x="70" y="105" width="160" height="15" rx="2" />
  <rect class="page-content" x="70" y="130" width="160" height="15" rx="2" />
  <rect class="page-content" x="70" y="155" width="120" height="15" rx="2" />
  <rect class="highlight" x="70" y="180" width="160" height="15" rx="2" />
  <rect class="page-content" x="70" y="205" width="160" height="15" rx="2" />
  <rect class="page-content" x="70" y="230" width="160" height="15" rx="2" />
  <rect class="page-content" x="70" y="255" width="100" height="15" rx="2" />
  
  <!-- AI Processing Circle -->
  <circle class="ai-circle" cx="300" cy="190" r="60" />
  <circle class="ai-core" cx="300" cy="190" r="20" />
  
  <!-- Arrows -->
  <path class="arrow" d="M260,190 L280,190" />
  <path class="arrow" d="M320,190 L340,190" />
  
  <!-- Summary Document -->
  <rect class="summary" x="350" y="100" width="200" height="180" rx="5" />
  <rect class="summary-line" x="370" y="130" width="160" height="10" rx="2" />
  <rect class="summary-line" x="370" y="150" width="160" height="10" rx="2" />
  <rect class="summary-line" x="370" y="170" width="120" height="10" rx="2" />
  <rect class="summary-line" x="370" y="190" width="160" height="10" rx="2" />
  <rect class="summary-line" x="370" y="210" width="100" height="10" rx="2" />
  
  <!-- Title -->
  <text x="370" y="120" font-family="Arial" font-size="14" font-weight="bold" fill="#4361ee">Summary</text>
</svg>`;

// Create avatar placeholders
const avatar1 = `<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="50" fill="#4361ee" />
  <circle cx="50" cy="40" r="20" fill="#ffffff" />
  <path d="M20,85 C20,65 80,65 80,85" fill="#ffffff" />
</svg>`;

const avatar2 = `<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="50" fill="#7209b7" />
  <circle cx="50" cy="40" r="20" fill="#ffffff" />
  <path d="M20,85 C20,65 80,65 80,85" fill="#ffffff" />
</svg>`;

const avatar3 = `<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
  <circle cx="50" cy="50" r="50" fill="#4cc9f0" />
  <circle cx="50" cy="40" r="20" fill="#ffffff" />
  <path d="M20,85 C20,65 80,65 80,85" fill="#ffffff" />
</svg>`;

// Create favicon
const favicon = `<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg">
  <rect width="32" height="32" rx="5" fill="#4361ee" />
  <rect x="8" y="8" width="16" height="3" rx="1" fill="white" />
  <rect x="8" y="14" width="16" height="3" rx="1" fill="white" />
  <rect x="8" y="20" width="10" height="3" rx="1" fill="white" />
</svg>`;

// Write files
fs.writeFileSync(path.join(imgDir, 'hero-illustration.svg'), heroIllustration);
fs.writeFileSync(path.join(imgDir, 'avatar-1.jpg'), avatar1);
fs.writeFileSync(path.join(imgDir, 'avatar-2.jpg'), avatar2);
fs.writeFileSync(path.join(imgDir, 'avatar-3.jpg'), avatar3);
fs.writeFileSync(path.join(imgDir, 'favicon.png'), favicon);

console.log('Created placeholder images for the landing page');
