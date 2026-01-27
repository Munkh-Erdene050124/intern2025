var merge_lt_dict = [];
fetch("/api/get-lt-dict")
    .then((response) => response.json())
    .then((data) => {
        merge_lt_dict = data;
    })
    .catch((error) => console.log(error));

var doc_dict = [];
fetch("/api/get-doc-dict")
    .then((response) => response.json())
    .then((data) => {
        doc_dict = data;
    })
    .catch((error) => console.log(error));

var coocur_dict = [];
fetch("/api/get-coocur-dict")
    .then((response) => response.json())
    .then((data) => {
        coocur_dict = data;
    })
    .catch((error) => console.log(error));

function goto_home() {
    window.location.replace("/");
}

var alert_del = document.querySelectorAll(".alert-del");
alert_del.forEach((x) =>
    x?.addEventListener("click", function () {
        x.parentElement.classList.add("hidden");
    })
);
var timeout = setTimeout(() => {
    var alert_del = document.querySelectorAll(".alert-del");
    alert_del.forEach((x) => x.parentElement.classList.add("hidden"));
}, 6000);

input = document.getElementById("dropzone-file");
input?.addEventListener("change", function (event) {
    let files = event.target.files;
    if (files.length > 0) {
        uploaded = document.getElementById("uploaded");
        uploaded.innerText = "(" + files[0].name + ", size: " + file_size_MB(files[0].size) + ")";
    }
});

function file_size_MB(size) {
    return (size / (1024 * 1024)).toFixed(2) + " MB";
}

document.querySelector("#menu-button")?.addEventListener("click", () => {
    let menu_class_list = document.querySelector("#menu").classList;
    if (menu_class_list.contains("hidden")) {
        menu_class_list.remove("hidden");
    } else {
        menu_class_list.add("hidden");
    }
});

var doc_legal_terms = document.getElementsByClassName("doc-legal-term");
for (let i = 0; i < doc_legal_terms?.length; i++) {
    doc_legal_terms[i]?.addEventListener("click", () => {
        let dlt = doc_legal_terms[i];
        const leg_term_docs = dlt.getElementsByClassName("leg-term-docs");
        if (leg_term_docs.length > 0) {
            leg_term_docs[0].remove();
        } else {
            let val = dlt.innerHTML.replace('<p class="w-fit text-left cursor-pointer text-business-color1 text-opacity-70 hover:text-opacity-100">', "").replace("</p>", "").trim();
            const mwe_id = val.split("-")[1];
            let coocur_list = coocur_dict.filter((coo) => coo.term_id * 1 === mwe_id * 1);
            let html_child = document.createElement("div");
            html_child.className = "leg-term-docs bg-business-color1 text-white px-2 py-1 rounded mx-2 mt-2 bg-opacity-40 transition-all duration-300 text-xs";
            const coocur_set = new Set(coocur_list.map((c) => c.doc_id));
            coocur_set.forEach(function (co) {
                const ddict = doc_dict.find((d) => d.doc_id === co);
                let a_tag = document.createElement("a");
                let br = document.createElement("br");
                a_tag.href = ddict?.doc_link ?? "https://legalinfo.mn/mn";
                a_tag.target = "_blank";
                a_tag.className = "w-full text-left ml-2 mb-2 hover:underline";
                a_tag.innerText = " - " + set_first_letter_to_upper(ddict?.doc_title) ?? "";
                html_child.appendChild(a_tag);
                html_child.appendChild(br);
            });
            doc_legal_terms[i].appendChild(html_child);
        }
    });
}

function set_first_letter_to_upper(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function show_lt(mwe_id) {
    let mwe_list = document.getElementsByClassName(mwe_id);
    for (let i = 0; i < mwe_list.length; i++) {
        lt_dict = merge_lt_dict.find((lt) => lt["id"] * 1 === mwe_id.split("_")[0] * 1);
        if (lt_dict) {
            mwe_list[i].title = lt_dict["leg_term"] ?? "";
        }
    }
}

function show_desc(mwe_id) {
    let mwe_tooltips = document.getElementsByClassName(mwe_id + "-tooltip");
    for (let i = 0; i < mwe_tooltips.length; i++) {
        lt_dict = merge_lt_dict.find((lt) => lt["id"] * 1 === mwe_id.split("_")[0] * 1);
        if (lt_dict) {
            class_list = mwe_tooltips[i].classList;
            if (class_list.contains("hidden")) {
                class_list.remove("hidden");
            } else {
                class_list.add("hidden");
            }
            mwe_tooltips[i].innerHTML = " - " + lt_dict["desc"] + ";" ?? "";
        }
    }
}

function start_analysis(btn_id) {
    let start_btn = document.getElementById(btn_id);
    start_btn.style = "opacity: 0.8;width: 100%";
    start_btn.innerHTML =
        '<svg aria-hidden="true" class="inline w-5 h-5 mr-2 text-white animate-spin fill-business-color1" viewBox="0 0 100 101" fill="none" xmlns="http://www.w3.org/2000/svg">' +
        '\n<path d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z" fill="currentColor"/>' +
        '\n<path d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z" fill="currentFill"/>' +
        "\n</svg>";
}

function analysis_user_doc() {
    let loading_with_js = document.getElementById("loader-spinning-with-js");
    let class_list = loading_with_js.classList;
    if (class_list.contains("hidden")) {
        class_list.remove("hidden");
        class_list.add("flex");
    }
}

function delete_user_doc(value) {
    let popup_modal = document.getElementById("popup-modal");
    let user_doc_id = value.replace("user_doc_", "") * 1;
    let pm_class_list = popup_modal.classList;
    if (pm_class_list.contains("hidden")) {
        pm_class_list.remove("hidden");
        pm_class_list.add("flex");
    }

    let confirm_btn = document.getElementById("popup-modal-comfirm-btn");
    if (confirm_btn) {
        confirm_btn.addEventListener("click", function () {
            fetch("/api/delete_user_doc", { method: "POST", body: JSON.stringify({ user_doc_id: user_doc_id }) })
                .then((data) => {
                    console.log("Successfully deleted.");
                    close_popup_modal();
                    document.location.reload();
                })
                .catch((error) => console.log(error));
        });
    }
}

function close_popup_modal() {
    let popup_modal = document.getElementById("popup-modal");
    let pm_class_list = popup_modal.classList;
    if (pm_class_list.contains("flex")) {
        pm_class_list.remove("flex");
        pm_class_list.add("hidden");
    }
}
