// Feature icons for the site
document.addEventListener('DOMContentLoaded', function() {
    // The hero illustration is now handled by the PNG image in the HTML
    
    // Create illustrations for the features section
    const featureIcons = document.querySelectorAll('.feature-icon');
    if (featureIcons.length > 0) {
        // Upload icon
        if (featureIcons[0]) {
            featureIcons[0].innerHTML = `
            <svg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
                <rect width="60" height="60" rx="30" fill="#f0f4ff" />
                <path d="M30 20v20M20 30l10-10 10 10" stroke="#4f46e5" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M20 40h20" stroke="#4f46e5" stroke-width="2" stroke-linecap="round"/>
            </svg>
            `;
        }
        
        // Process icon
        if (featureIcons[1]) {
            featureIcons[1].innerHTML = `
            <svg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
                <rect width="60" height="60" rx="30" fill="#ecfdf5" />
                <circle cx="30" cy="30" r="15" fill="none" stroke="#10b981" stroke-width="2"/>
                <path d="M30 20v10l7 7" stroke="#10b981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            `;
        }
        
        // AI icon
        if (featureIcons[2]) {
            featureIcons[2].innerHTML = `
            <svg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg">
                <rect width="60" height="60" rx="30" fill="#f0f9ff" />
                <rect x="20" y="20" width="20" height="20" rx="2" fill="none" stroke="#0ea5e9" stroke-width="2"/>
                <circle cx="25" cy="25" r="2" fill="#0ea5e9"/>
                <circle cx="35" cy="25" r="2" fill="#0ea5e9"/>
                <path d="M25 35h10" stroke="#0ea5e9" stroke-width="2" stroke-linecap="round"/>
            </svg>
            `;
        }
    }
});
