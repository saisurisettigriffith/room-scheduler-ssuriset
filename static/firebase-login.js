'use strict';

import {initializeApp} from "https://www.gstatic.com/firebasejs/9.22.2/firebase-app.js";
import {getAuth, createUserWithEmailAndPassword, signInWithEmailAndPassword, signOut} from "https://www.gstatic.com/firebasejs/9.22.2/firebase-auth.js"


window.addEventListener("load", function() {
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);
    updateUI(document.cookie);

    document.addEventListener('DOMContentLoaded', function () {
        const tweetTextArea = document.getElementById('tweet');
        const charCountSpan = document.getElementById('char-count');

        tweetTextArea.addEventListener('input', function () {
            const remaining = 140 - tweetTextArea.value.length;
            charCountSpan.textContent = remaining;

            // Optional: Prevent typing beyond 140 characters
            if (remaining < 0) {
                tweetTextArea.value = tweetTextArea.value.substr(0, 140);
            }
        });
    });

    document.getElementById("sign-up").addEventListener('click', function() {
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        createUserWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            const user = userCredential.user;
            user.getIdToken().then((token) => {
                document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                window.location = "/";
            });
        })
        .catch((error) => {
            console.log(error.code+error.message);
        })
    });

    document.getElementById("login").addEventListener('click', function() {
        const email = document.getElementById("email").value;
        const password = document.getElementById("password").value;

        signInWithEmailAndPassword(auth, email, password)
        .then((userCredential) => {
            const user = userCredential.user;
            console.log("logged in");

            user.getIdToken().then((token) => {
                document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                window.location = "/";
            });
        })
        .catch((error) => {
            console.log(error.code + error.message);
        })
    });

    document.getElementById("sign-out").addEventListener('click', function() {
        signOut(auth)
        .then((output) => {
            document.cookie = "token=;path=/;SameSite=Strict";
            window.location = "/";
        })
    });
    
});

function updateUI(cookie) {
    var token = parseCookieToken(cookie);

    if(token.length > 0) {
        document.getElementById("login-box").hidden = true;
        document.getElementById("logout-box").hidden = false;
    } else {
        document.getElementById("login-box").hidden = false;
        document.getElementById("logout-box").hidden = true;
    }
}

function parseCookieToken(cookie) {
    var fun = "";
    var strings = cookie.split(';');

    for (let i = 0; i < strings.length; i++) {
        var temp = strings[i].split('=');
        if (temp[0] == "token") {
                fun = temp[1];
        }
    }
    return fun;
}