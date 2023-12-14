document.getElementById('routeForm').addEventListener('submit', function(event){
    let start = document.getElementById('start_location').value;
    let end = document.getElementById('end_location').value;
    console.log(start)
    console.log(end)

    if (!start || !end) {
        alert('Please enter both starting and ending locations.');
        event.preventDefault();
    }
});
