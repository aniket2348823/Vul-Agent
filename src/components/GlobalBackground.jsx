import React, { useEffect, useRef } from 'react';

const GlobalBackground = () => {
    const starsRef = useRef(null);

    useEffect(() => {
        if (starsRef.current) {
            starsRef.current.innerHTML = '';
            for (let i = 0; i < 300; i++) {
                const star = document.createElement('div');
                star.className = 'star';
                const size = Math.random() * 1.5;
                star.style.left = `${Math.random() * 100}%`;
                star.style.top = `${Math.random() * 100}%`;
                star.style.width = `${size}px`;
                star.style.height = `${size}px`;
                star.style.opacity = Math.random() * 0.4 + 0.1;

                // Varied animation duration and delay for organic twinkling
                const duration = 2 + Math.random() * 4;
                const delay = Math.random() * 5;
                star.style.animation = `twinkle ${duration}s infinite ease-in-out ${delay}s`;

                starsRef.current.appendChild(star);
            }
        }
    }, []);

    return (
        <div className="fixed inset-0 z-[-1] pointer-events-none overflow-hidden select-none">
            {/* Stars Layer Only - Transparent Overlay */}
            <div ref={starsRef} className="absolute inset-0"></div>

            <style>{`
                @keyframes twinkle {
                    0%, 100% { opacity: 0.1; transform: scale(0.8); }
                    50% { opacity: 0.8; transform: scale(1.1); }
                }
                .star {
                    position: absolute;
                    background: white;
                    border-radius: 50%;
                    box-shadow: 0 0 4px rgba(255, 255, 255, 0.4);
                }
            `}</style>
        </div>
    );
};

export default GlobalBackground;
