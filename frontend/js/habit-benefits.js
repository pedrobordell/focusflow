// Funcionalidad para señalar la información de cada tipo de hábito
window.HabitBenefits = (function() {

    var habitBenefits = {
        "Health": "Take care of your body and improve your well-being every day.",
        "Fitness": "Boost your energy, build strength, and improve your fitness.",
        "Study": "Learn, develop your skills, and achieve your goals.",
        "Productivity": "Manage your time better and make progress towards your goals.",
        "Mindfulness": "Reduce stress and improve your focus and mental well-being.",
        "Social": "Strengthen your relationships and enjoy more moments with others.",
        "Finance": "Improve your financial habits and build a more secure future.",
        "Other": "Create personalized habits for any area of your life.",
        "": "Discover how small habits can lead to big changes.",
    };


    function attachText() {
        var habitSelect = document.getElementById("habitType");
        var option = habitSelect.value;
        var habitText = document.getElementById("habitBenefitsText");
        
        habitText.textContent = habitBenefits[option];
    }

    return {
        attachText: attachText,
    }
})();
