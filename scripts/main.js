// Main application logic
let menu_tab = 0
let tags_list = []
let classes_counter = 0
let editingClassGroupName = ""
let classes_groups = {
    default: {
        name:  "Padrão",
        class_1: {
            name: "Passado",
            description: ""
        },
        class_2: {
            name: "Histórico",
            description: ""
        },
        class_3: {
            name: "Previsão",
            description: ""
        },
    }
}

var form = document.getElementById("ClassesForm");
function handleForm(event) { 
    event.preventDefault(); 
    saveClassGroupEdit() 
} 
form.addEventListener('submit', handleForm);

function readClasses(){
    let classes_editor = document.getElementById("classes_editor")
    let class_group = document.getElementById("class_group")

    while (class_group.children[1].disabled != class_group.lastElementChild.disabled) {
        class_group.removeChild(class_group.lastChild);
    }
    while (classes_editor.children[1].disabled != classes_editor.lastElementChild.disabled) {
        classes_editor.removeChild(classes_editor.lastChild);
    }

    for (const [key, value] of Object.entries(classes_groups)){
        classes_editor.insertAdjacentHTML("beforeend", `
            <option value="${key}">
                <div class="custom-option">
                    <span class="option-text">${value.name}</span>
                </div>
            </option>
        `)
    }
    for (const [key, value] of Object.entries(classes_groups)){
        console.log("key")
        class_group.insertAdjacentHTML("beforeend", `
            <option value="${key}">
                <div class="custom-option">
                    <span class="option-text">${value.name}</span>
                </div>
            </option>
        `)
    }
}
readClasses()

function handleClassSelect(){
    let content = document.getElementById("class_content")
    let classes_editor = document.getElementById("classes_editor")
    let add_class = document.getElementById("add_class")
    add_class.style.display = "flex"
    editingClassGroupName = classes_editor.value
    data = classes_groups[classes_editor.value]

    content.innerHTML = ""
    classes_counter = 0
    for(const parameter in data){
        console.log(parameter)
        if(classes_counter==0){
            content.insertAdjacentHTML("beforeend", `
                <div class="input_group">
                    <label for="class_name">Nome</label>
                    <input id="class_name" name="class_name" type="text" placeholder="Nome do grupo de classificações" value="${data.name}">
                </div>
                <hr style="color:#646464; background:#646464;border:#646464">
            `)
        } else{
            content.insertAdjacentHTML("beforeend", `
                <div class="input_group" style="margin-top: 15px">
                    <label for="class_category_${classes_counter}">Categoria ${classes_counter}</label>
                    <input id="category_${classes_counter}" name="class_category_${classes_counter}" type="text" placeholder="Nome da categoria" value="${data[parameter].description}">
                    <textarea name="" id="description_${classes_counter}" placeholder="Informe a descrição da categoria"></textarea>
                </div>
            `)
        }
        
        classes_counter++
    }
    
}

function handleNewClassGroup(){
    let content = document.getElementById("class_content")
    let classes_editor = document.getElementById("classes_editor")
    let add_class = document.getElementById("add_class")
    console.log(editingClassGroupName)
    add_class.style.display = "flex"
    data = classes_groups[classes_editor.value]

    content.innerHTML = ""
    classes_counter = 2
    content.insertAdjacentHTML("beforeend", `
        <div class="input_group">
            <label for="class_name">Nome</label>
            <input id="class_name" name="class_name" type="text" placeholder="Nome do grupo de classificações" value="">
        </div>
        <hr style="color:#646464; background:#646464;border:#646464">
    `)
    content.insertAdjacentHTML("beforeend", `
        <div class="input_group" style="margin-top: 15px">
            <label for="class_category_1">Categoria 1</label>
            <input id="category_1" name="class_category_1" type="text" placeholder="Nome da categoria" value="">
            <textarea name="" id="description_1" placeholder="Informe a descrição da categoria"></textarea>
        </div>
    `)
}

function addClassGroup(){
    class_group_name = `group_${Object.keys(classes_groups).length+1}`
    classes_groups[`group_${Object.keys(classes_groups).length+1}`] = {
        name:"",
        class_1: {
            name: "",
            description: ""
        }
    }
    editingClassGroupName = `group_${Object.keys(classes_groups).length}`
    console.log(classes_groups)
    handleNewClassGroup()
    console.log("finished")
}

function addClass(){
    let content = document.getElementById("class_content")
    let classes_editor = document.getElementById("classes_editor")
    let class_name = document.getElementById("class_name")
    data = classes_groups[class_name.value]

    classes_counter++
    content.insertAdjacentHTML("beforeend", `
        <div class="input_group" style="margin-top: 15px">
            <label for="category_name">Categoria ${classes_counter}</label>
            <input id="category_${classes_counter}" name="class_category_${classes_counter}" type="text" placeholder="Nome da categoria" value="">
            <textarea name="" id="description_${classes_counter}" placeholder="Informe a descrição da categoria"></textarea>
        </div>
    `)
}

function saveClassGroupEdit(){
    console.log(classes_counter)
    for(let i=1;i<classes_counter;i++) {
        let category = document.getElementById(`category_${i}`)
        let description = document.getElementById(`description_${i}`)
        let class_name = document.getElementById(`class_name`)

        classes_groups[editingClassGroupName]["name"] = class_name.value
        classes_groups[editingClassGroupName][`class_${i}`]["name"] = category.value
        classes_groups[editingClassGroupName][`class_${i}`]["description"] = description.value
        console.log(classes_groups)
    }
    readClasses()
    showNotification()
    let content = document.getElementById("class_content")
    content.innerHTML = ""
}

function writeTags(){
    let tags = document.getElementById("tags")
    console.log(tags_list)
    tags.innerHTML = ""
    tags.innerText = ""
    tags_list.forEach((el,i) => {
        tags.insertAdjacentHTML("beforeend", `
        <div id="tag_${el}" class="tag">
            ${el}
            <i class="tag_del fi fi-rr-cross-small" onclick="delTag('${el}')"></i>
        </div>
        `)
    })
}

function addTag(tag){
    console.log(tag)
    console.log(tags_list.includes(tag))
    if(tags_list.includes(tag)) {return}
    tags_list.push(tag)
    writeTags()
    clearFieldError('tags_selector')
}

function delTag(tag){
    tags_list = tags_list.filter(item => item !== tag)
    writeTags()
    if (tags_list.length > 0) {
        clearFieldError('tags_selector')
    }
}

function handleTagInput(key) {
    let tags_selector = document.getElementById("tags_selector")
    if (key.code === 'Space' || key.code === 'Enter' || key.code === "Tab") {
        key.preventDefault();
        const tagValue = tags_selector.value.trim();
        
        if (key.code === 'Enter') {
            // If Enter is pressed
            if (tagValue) {
                // If there's text, add the tag and stay in field
                addTag(tagValue);
                writeTags();
                tags_selector.value = "";
                clearFieldError('tags_selector');
            } else {
                // If no text, move to next field
                moveToNextField('tags_selector');
            }
        } else {
            // For Space and Tab, add tag if there's text
            if (tagValue) {
                addTag(tagValue);
                writeTags();
                tags_selector.value = "";
                clearFieldError('tags_selector');
            }
        }
    }
}

function moveToNextField(currentFieldId) {
    // Define the order of fields
    const fieldOrder = [
        'tags_selector',
        'media_outlet',
        'class_group',
        'max_news',
        'submit'
    ];
    
    const currentIndex = fieldOrder.indexOf(currentFieldId);
    if (currentIndex === -1) return;
    
    // Get next field index
    const nextIndex = currentIndex + 1;
    
    // If we're at the last field (max_news), focus submit button
    if (nextIndex === fieldOrder.length - 1) {
        const submitButton = document.getElementById('submit');
        if (submitButton) {
            submitButton.focus();
        }
        return;
    }
    
    // If we're at submit button, don't do anything (form will submit)
    if (currentFieldId === 'submit') {
        return;
    }
    
    // Focus next field
    const nextFieldId = fieldOrder[nextIndex];
    const nextField = document.getElementById(nextFieldId);
    
    if (nextField) {
        // For max_news, check if it's enabled
        if (nextFieldId === 'max_news') {
            const maxNewsSwitch = document.getElementById('max_news_switch');
            if (maxNewsSwitch && !maxNewsSwitch.checked) {
                // If max_news is disabled, skip to submit button
                const submitButton = document.getElementById('submit');
                if (submitButton) {
                    submitButton.focus();
                }
                return;
            }
        }
        nextField.focus();
        
        // For select elements, we might want to open them
        if (nextField.tagName === 'SELECT') {
            // Try to trigger click to open dropdown (browser dependent)
            setTimeout(() => {
                nextField.click();
            }, 10);
        }
    }
}

function switchTabs(tab){
    let home_tab = document.getElementById("home_tab")
    let classes_tab = document.getElementById("classes_tab")
    let info_tab = document.getElementById("info_tab")
    let home_tab_text = document.getElementById("home_tab_text")
    let classes_tab_text = document.getElementById("classes_tab_text")
    let info_tab_text = document.getElementById("info_tab_text")

    let home_section = document.getElementById("home_section")
    let classes_section = document.getElementById("classes_section")
    let info_section = document.getElementById("info_section")

    if (tab == 0){
        home_tab.classList.add("selected")
        classes_tab.classList.remove("selected")
        info_tab.classList.remove("selected")
        home_section.style.display = "inline-block"
        classes_section.style.display = "none"
        info_section.style.display = "none"
        
        home_tab_text.classList.add("show")
        classes_tab_text.classList.remove("show")
        info_tab_text.classList.remove("show")
    } else if(tab == 1){
        home_tab.classList.remove("selected")
        classes_tab.classList.add("selected")
        info_tab.classList.remove("selected")
        home_section.style.display = "none"
        classes_section.style.display = "inline-block"
        info_section.style.display = "none"
        
        home_tab_text.classList.remove("show")
        classes_tab_text.classList.add("show")
        info_tab_text.classList.remove("show")
    } else if(tab == 2){
        home_tab.classList.remove("selected")
        classes_tab.classList.remove("selected")
        info_tab.classList.add("selected")
        home_section.style.display = "none"
        classes_section.style.display = "none"
        info_section.style.display = "inline-block"
        
        home_tab_text.classList.remove("show")
        classes_tab_text.classList.remove("show")
        info_tab_text.classList.add("show")
    }
}

function fetch_news(path, method, requestData={}){
    payload = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        },
    }
    if (method == "POST"){
        payload["body"] = JSON.stringify(requestData)
    }
    
    return fetch("http://127.0.0.1:5555"+path, payload)
    .then(response => response.json())
    .then(data => {
        return data
    })
    .catch(error => {
        console.error('Erro na requisição:', error);
        return {"status": "error"}
    });
}

checkDownload = 0
function CheckDownload(){
    console.log("checking")
    if (document.getElementById('downloadBtn').checkVisibility()) {
        console.log("ok")
        clearInterval(checkDownload)
        return 
    }

    fetch_news("/finished", "GET").then((r) => {
        if (r){
            document.getElementById('downloadBtn').style.display = "flex";
            console.log("bolas")
        }
    })
}

function showFieldError(fieldId, message) {
    // Remove existing error message if any
    const existingError = document.getElementById(`${fieldId}_error`);
    if (existingError) {
        existingError.remove();
    }
    
    // Find the input group container
    const field = document.getElementById(fieldId);
    if (!field) return;
    
    const inputGroup = field.closest('.input_group');
    if (!inputGroup) return;
    
    // Create error message element
    const errorElement = document.createElement('div');
    errorElement.id = `${fieldId}_error`;
    errorElement.className = 'field-error';
    errorElement.textContent = message;
    
    // Insert error message after the field or its container
    if (fieldId === 'tags_selector') {
        const tagsContainer = document.getElementById('tags');
        if (tagsContainer && tagsContainer.parentNode) {
            tagsContainer.parentNode.insertBefore(errorElement, tagsContainer.nextSibling);
        } else {
            inputGroup.appendChild(errorElement);
        }
    } else if (fieldId === 'max_news') {
        const maxNewsContainer = document.getElementById('max_news_container');
        if (maxNewsContainer && maxNewsContainer.parentNode) {
            maxNewsContainer.parentNode.insertBefore(errorElement, maxNewsContainer.nextSibling);
        } else {
            inputGroup.appendChild(errorElement);
        }
    } else {
        inputGroup.appendChild(errorElement);
    }
}

function clearFieldError(fieldId) {
    const errorElement = document.getElementById(`${fieldId}_error`);
    if (errorElement) {
        errorElement.remove();
    }
}

function validateForm() {
    let isValid = true;
    
    // Clear all previous errors
    document.querySelectorAll('.field-error').forEach(error => error.remove());
    
    // Validate tags
    if (tags_list.length === 0) {
        showFieldError('tags_selector', 'Por favor, adicione pelo menos uma palavra-chave');
        isValid = false;
    }
    
    // Validate media outlet
    const media_outlet = document.getElementById('media_outlet').value;
    if (!media_outlet || media_outlet === '_') {
        showFieldError('media_outlet', 'Por favor, selecione um veículo de notícia');
        isValid = false;
    }
    
    // Validate class group
    const class_group = document.getElementById('class_group').value;
    if (!class_group || class_group === '_') {
        showFieldError('class_group', 'Por favor, selecione um grupo de categorias');
        isValid = false;
    }
    
    // Validate max_news (only if switch is checked)
    const max_news_switch = document.getElementById('max_news_switch');
    const max_news = document.getElementById('max_news');
    if (max_news_switch && max_news_switch.checked) {
        if (!max_news.value || max_news.value.trim() === '') {
            showFieldError('max_news', 'Por favor, informe o número máximo de notícias');
            isValid = false;
        } else if (isNaN(parseInt(max_news.value)) || parseInt(max_news.value) <= 0) {
            showFieldError('max_news', 'Por favor, informe um número válido');
            isValid = false;
        }
    }
    
    return isValid;
}

function mostrarDownload(event) {
    event.preventDefault();
    
    // Validate form before proceeding
    if (!validateForm()) {
        return;
    }
    
    document.getElementById('downloadBtn').style.display = "none";
    console.log("bolas2")

    const palavra = tags_list.join(" ");
    const media_outlet = document.getElementById('media_outlet').value;
    const max_news = document.getElementById('max_news').value == "" ? 50 : document.getElementById('max_news').value;
    
    console.log("Palavra-chave:", palavra);
    console.log("Fonte:", media_outlet);
    console.log("Número máximo de notícias:", max_news);

    const requestData = {
        keyword: palavra,
        fonte: media_outlet,
        max_news: parseInt(max_news)
    };

    fetch_news("", "POST", requestData).then((r) => {
        console.log("Resposta da API:", r)
    })

    checkDownload = setInterval(CheckDownload, 1000)
    
}

setInterval(() => {
    fetch_news("/busy", "GET").then((r) =>{
        currentText = document.getElementById("submit").textContent
        if (r) {
            document.getElementById("submit").textContent = currentText == "Loading." ? "Loading.." : currentText == "Loading.."? "Loading..." :currentText == "Loading..."? "Loading." : "Loading."  
        }else if (currentText != "Buscar"){
            document.getElementById("submit").textContent = "Buscar"
        }
    })
        
}, 500)

function yast_reset() {
    // Clear all error messages
    document.querySelectorAll('.field-error').forEach(error => error.remove());
    
    // Clear tags
    tags_list = [];
    writeTags();
    
    // Reset tags input
    const tags_selector = document.getElementById("tags_selector");
    if (tags_selector) {
        tags_selector.value = "";
    }
    
    // Reset media outlet select
    const media_outlet = document.getElementById("media_outlet");
    if (media_outlet) {
        media_outlet.value = "_";
    }
    
    // Reset max news input and switch
    const max_news_switch = document.getElementById("max_news_switch");
    const max_news = document.getElementById("max_news");
    const max_news_asterisk = document.getElementById("max_news_asterisk");
    if (max_news_switch) {
        max_news_switch.checked = false;
    }
    if (max_news) {
        max_news.value = "";
        max_news.disabled = true;
    }
    if (max_news_asterisk) {
        max_news_asterisk.classList.remove("active");
    }
    
    // Reset class group select
    const class_group = document.getElementById("class_group");
    if (class_group) {
        class_group.value = "_";
    }
    
    // Clear checkDownload interval
    if (checkDownload) {
        clearInterval(checkDownload);
        checkDownload = 0;
    }
    
    // Hide download button
    const downloadBtn = document.getElementById("downloadBtn");
    if (downloadBtn) {
        downloadBtn.style.display = "none";
    }
    
    // Reset submit button text
    const submit = document.getElementById("submit");
    if (submit) {
        submit.textContent = "Buscar";
    }
    
    // Hide wifi loader
    const wifi_loader = document.getElementById("wifi-loader");
    if (wifi_loader) {
        wifi_loader.style.display = "none";
    }
    
    console.log("App reset to default state");
}

function baixarArquivo() {
    // Faz requisição para a API para obter o arquivo
    fetch("http://127.0.0.1:5555/file")
    .then(response => {
        if (!response.ok) {
            throw new Error('Erro ao baixar arquivo da API');
        }
        return response.blob();
    })
    .then(blob => {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = 'resultados.xlsx';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Reset app after download completes
        yast_reset();
    })
    .catch(error => {
        console.error('Erro ao baixar arquivo:', error);
    });
}

window.onload = function() {
    document.getElementById('downloadBtn').addEventListener('click', baixarArquivo);
    
    // Add event listeners to clear errors when fields change
    const media_outlet = document.getElementById('media_outlet');
    if (media_outlet) {
        media_outlet.addEventListener('change', () => clearFieldError('media_outlet'));
        // Handle Enter key to move to next field
        media_outlet.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                moveToNextField('media_outlet');
            }
        });
    }
    
    const class_group = document.getElementById('class_group');
    if (class_group) {
        class_group.addEventListener('change', () => clearFieldError('class_group'));
        // Handle Enter key to move to next field
        class_group.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                moveToNextField('class_group');
            }
        });
    }
    
    const max_news = document.getElementById('max_news');
    if (max_news) {
        max_news.addEventListener('input', () => clearFieldError('max_news'));
        // Handle Enter key to move to submit button
        max_news.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                moveToNextField('max_news');
            }
        });
    }
    
    const max_news_switch = document.getElementById('max_news_switch');
    if (max_news_switch) {
        max_news_switch.addEventListener('change', () => clearFieldError('max_news'));
    }
    
    // Prevent form submission on Enter in input fields (except submit button)
    const form = document.getElementById('search-form');
    if (form) {
        form.addEventListener('keydown', (e) => {
            // Only prevent if Enter is pressed and focus is not on submit button
            if (e.key === 'Enter' && e.target.id !== 'submit' && e.target.tagName !== 'BUTTON') {
                // Let the individual field handlers manage the behavior
                // This prevents default form submission
                if (e.target.id !== 'tags_selector' && 
                    e.target.id !== 'media_outlet' && 
                    e.target.id !== 'class_group' && 
                    e.target.id !== 'max_news') {
                    e.preventDefault();
                }
            }
        });
    }
    
    // Handle Enter on submit button to submit form
    const submitButton = document.getElementById('submit');
    if (submitButton) {
        submitButton.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                // Let the form submit naturally
                // The form's onsubmit handler will validate
            }
        });
    }
}


