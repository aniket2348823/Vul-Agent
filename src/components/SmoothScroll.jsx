import { ReactLenis } from 'lenis/react';

const SmoothScroll = ({ children }) => {
    return (
        <ReactLenis root options={{ lerp: 0.1, duration: 1.2, smoothWheel: true }}>
            {children}
        </ReactLenis>
    );
};

export default SmoothScroll;
