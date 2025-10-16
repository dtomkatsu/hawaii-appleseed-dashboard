(function() {
    'use strict';

    // Wait for Streamlit to be ready
    function onStreamlitReady(callback) {
        if (window.Streamlit === undefined) {
            console.log('Waiting for Streamlit...');
            setTimeout(function() { onStreamlitReady(callback); }, 100);
        } else {
            console.log('Streamlit is ready');
            callback();
        }
    }

    // Scroll indicator functionality
    function initScrollIndicator() {
        var panel = document.querySelector('.info-panel.visible');
        if (!panel) {
            console.log('No visible panel found, retrying...');
            setTimeout(initScrollIndicator, 500);
            return;
        }

    // Remove any existing scroll indicators
    var existingIndicator = document.querySelector('.scroll-indicator');
    if (existingIndicator) {
        existingIndicator.remove();
    }

    // Create scroll indicator arrow
    var scrollArrow = document.createElement('div');
    scrollArrow.className = 'scroll-indicator down';
    scrollArrow.innerHTML = '▼';
    document.body.appendChild(scrollArrow); // Append to body instead of panel
    
    console.log('Scroll indicator created:', scrollArrow);

    function updateScrollIndicator() {
        var scrollTop = panel.scrollTop;
        var scrollHeight = panel.scrollHeight;
        var clientHeight = panel.clientHeight;
        
        // Check if content is scrollable
        if (scrollHeight <= clientHeight) {
            scrollArrow.style.display = 'none';
            return;
        }
        
        scrollArrow.style.display = 'block';
        
        // Check if at bottom (with small tolerance)
        var isAtBottom = scrollTop >= (scrollHeight - clientHeight - 5);
        
        if (isAtBottom) {
            scrollArrow.innerHTML = '▲'; // Up arrow
            scrollArrow.className = 'scroll-indicator up';
        } else {
            scrollArrow.innerHTML = '▼'; // Down arrow
            scrollArrow.className = 'scroll-indicator down';
        }
    }
    
    // Click handler for the arrow
    scrollArrow.addEventListener('click', function() {
        var scrollTop = panel.scrollTop;
        var scrollHeight = panel.scrollHeight;
        var clientHeight = panel.clientHeight;
        var isAtBottom = scrollTop >= (scrollHeight - clientHeight - 5);
        
        if (isAtBottom) {
            // Scroll to top
            panel.scrollTo({ top: 0, behavior: 'smooth' });
        } else {
            // Scroll to bottom
            panel.scrollTo({ top: scrollHeight, behavior: 'smooth' });
        }
    });
    
    // Initial setup
    updateScrollIndicator();
    
    // Update on scroll
    panel.addEventListener('scroll', updateScrollIndicator);
    
    // Update on resize (with debounce)
    var resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(updateScrollIndicator, 100);
    });
    
    // Cleanup function
    var cleanup = function() {
        console.log('Cleaning up scroll indicator');
        panel.removeEventListener('scroll', updateScrollIndicator);
        window.removeEventListener('resize', updateScrollIndicator);
        if (scrollArrow && scrollArrow.parentNode) {
            scrollArrow.parentNode.removeChild(scrollArrow);
        }
    };
    
    // Clean up when panel is closed
    var observer = new MutationObserver(function(mutations) {
        if (!document.body.contains(panel)) {
            cleanup();
            observer.disconnect();
        }
    });
    observer.observe(document.body, { childList: true, subtree: true });
    
    return cleanup;
}

    // Initialize when Streamlit is ready
    onStreamlitReady(function() {
        // Small delay to ensure DOM is fully rendered
        setTimeout(initScrollIndicator, 1000);
    });
})();
