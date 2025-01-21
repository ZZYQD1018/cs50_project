document.addEventListener('DOMContentLoaded', () => {

    console.log('DOM fully loaded and parsed'); // Debugging
    
    const header = document.getElementById('movable-header');
    const hoverArea = document.createElement('div');

    // Create a hover area to detect mouse entry
    hoverArea.id = 'hover-area';
    document.body.appendChild(hoverArea);

    console.log('Hover area appended to the body:', hoverArea); // Debugging

    let isHeaderVisible = true; // Default to visible for debugging

    // Show the header when the mouse enters the hover area
    hoverArea.addEventListener('mouseenter', () => {
        console.log('Mouse entered hover area');
        header.style.transform = 'translateY(0)'; // Show header
        isHeaderVisible = true;
    });

    // Hide the header when the mouse leaves the header
    header.addEventListener('mouseleave', () => {
        console.log('Mouse left header');
        if (isHeaderVisible) {
            header.style.transform = 'translateY(-100%)'; // Hide header
            isHeaderVisible = false;
        }
    });

    // Debugging: Log hover area creation
    console.log('Hover area created:', hoverArea);
});
