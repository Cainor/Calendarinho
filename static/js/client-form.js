// Function to update the client select2 dropdown with a new option
function updateClientSelect(id, name) {
    var select2 = $('#id_client');
    var option = new Option(name, id, true, true);
    select2.append(option).trigger('change');
}

// Function to open the popup window for creating a new client
function openPopup(url) {
    // Open popup window
    var popup = window.open(url, 'clientPopup', 'width=600,height=600,resizable=yes,scrollbars=yes');
    
    // Center the popup
    if (popup) {
        var x = (screen.width - 600) / 2;
        var y = (screen.height - 600) / 2;
        popup.moveTo(x, y);
    }
    
    return false;
}
