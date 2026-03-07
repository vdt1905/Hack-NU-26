import React from 'react';
import { Toaster, toast } from 'react-hot-toast';

export const ToastProvider = ({ children }) => {
    return (
        <>
            {children}
            <Toaster
                position="top-right"
                toastOptions={{
                    duration: 3000,
                    style: {
                        background: 'var(--color-surface-100)',
                        color: 'var(--color-text-main)',
                        border: '1px solid var(--color-surface-200)',
                        borderRadius: 'var(--radius-md)',
                        boxShadow: 'var(--shadow-floating)',
                    },
                    success: {
                        iconTheme: {
                            primary: 'var(--color-primary-500)',
                            secondary: '#fff',
                        },
                    },
                    error: {
                        iconTheme: {
                            primary: '#ef4444',
                            secondary: '#fff',
                        },
                    },
                }}
            />
        </>
    );
};

// Custom hook to maintain compatibility with existing codebase
export const useToast = () => {
    return {
        toast: ({ title, description, variant = 'info' }) => {
            const message = description ? `${title}: ${description}` : title;

            if (variant === 'success') {
                toast.success(message);
            } else if (variant === 'error' || variant === 'destructive') {
                toast.error(message);
            } else {
                toast(message);
            }
        }
    };
};
