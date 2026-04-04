document.addEventListener("DOMContentLoaded", function () {

    console.log("StuMarket UI cargado correctamente");

    // Animación suave en cards
    const cards = document.querySelectorAll(".card-modern");

    cards.forEach(card => {
        card.addEventListener("mouseenter", () => {
            card.style.transform = "translateY(-4px)";
        });

        card.addEventListener("mouseleave", () => {
            card.style.transform = "translateY(0)";
        });
    });

});