/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        './core/templates/**/*.html',
        './core/templates/**/**/*.html',
        './static/**/*.js',
    ],
    theme: {
        extend: {
            // okay so I spent like an hour getting these exact colors from the images
            // used a color picker tool and everything lol
            colors: {
                // EDUSTREAM brand colors - finally got them right!
                'edustream-navy': '#0F172A',  // main background, so dark and clean
                'edustream-slate': '#1E293B',  // card backgrounds
                'edustream-emerald': '#10B981',  // THE green color, super important
                'edustream-border': '#334155',  // subtle borders on cards

                // text colors (took me a while to figure out the right shades)
                'text-primary': '#F8FAFC',
                'text-secondary': '#94A3B8',
                'text-muted': '#64748B',
            },

            // Bento card styling - these rounded corners look so good
            borderRadius: {
                'bento': '16px',  // the signature bento rounded corner size
                'bento-lg': '20px',  // for bigger cards
            },

            // box shadows for the cards (trying to match the reference images exactly)
            boxShadow: {
                'bento': '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
                'bento-lg': '0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3)',
            },

            // spacing for the grid gaps
            spacing: {
                'bento-gap': '24px',  // standard gap between bento cards
            },

            // custom animations (might add more later)
            animation: {
                'fade-in': 'fadeIn 0.3s ease-in-out',
            },

            keyframes: {
                fadeIn: {
                    '0%': { opacity: '0', transform: 'translateY(10px)' },
                    '100%': { opacity: '1', transform: 'translateY(0)' },
                }
            }
        },
    },
    plugins: [],
}
