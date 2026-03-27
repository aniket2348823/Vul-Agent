import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LIQUID_SPRING } from '../lib/constants';

const pageVariants = {
    initial: {
        opacity: 0,
        y: 20,
        scale: 0.98
    },
    in: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: LIQUID_SPRING
    },
    out: {
        opacity: 0,
        y: -10,
        scale: 1.01,
        transition: {
            duration: 0.2
        }
    }
};

const AnimationWrapper = ({ children, className }) => {
    return (
        <motion.div
            initial="initial"
            animate="in"
            exit="out"
            variants={pageVariants}
            className={className}
        >
            {children}
        </motion.div>
    );
};

export default AnimationWrapper;
