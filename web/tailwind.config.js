module.exports = {
    mode: "jit",
    content: ["./main_app/templates/**/*.{html,htm}"],
    theme: {
        extend: {
            colors: {
                "business-color-default": "rgb(4, 19, 120)",
                "business-color1": "rgb(13, 57, 156)",
                "business-color2": "rgb(0, 51, 153)",
                "business-color3": "rgb(83, 113, 255)",
            },
            blur: {
                xs: "2px",
            },
            backgroundImage: {
                "how-its-work": "url(../images/seq-dia.png)",
            },
        },
    },
    plugins: [require("@tailwindcss/forms")],
};
