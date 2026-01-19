/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/templates/**/*.html",
    "./node_modules/flowbite/**/*.js"
  ],
  plugins: [
    require("flowbite/plugin")
  ]
}
