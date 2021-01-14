var addButton = document.getElementById("addButton")
addButton.addEventListener("click", (ev) => {
	window.location.href = "/sender/dashboard/new"
	})
	
var tab = document.getElementById("tab")
var rowsNumber = tab.children[0].children.length
const buttonColNumber = 5

for(var i = 1; i < rowsNumber; i++) {
	var row = tab.children[0].children[i]
	var button = row.children[buttonColNumber].children[0]
	button.addEventListener("click", deleteRowData)
}

function deleteRowData(ev)
{
	var pid = ev.target.parentNode.parentNode.children[0].innerText
	var endpoint = "/sender/dashboard/" + pid
	var xhr = new XMLHttpRequest()
	xhr.open('DELETE', endpoint)
	xhr.onreadystatechange = function() {
		location.reload()
	}
	xhr.send(null);
}
