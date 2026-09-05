// firebase.js (Ensure this file exists in frontend/src/)
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

// 🔹 Your Firebase Config (Replace with your actual credentials)
const firebaseConfig = {
    apiKey: "AIzaSyDdroTDmNz7OuP8Cotur7YlFGjiMJz_YxA",
    authDomain: "alpr-e1057.firebaseapp.com",
    projectId: "alpr-e1057",
    storageBucket: "alpr-e1057.firebasestorage.app",
    messagingSenderId: "797324359450",
    appId: "1:797324359450:web:5339dec9dc843ce3471ea3"
  };

// 🔥 Initialize Firebase
const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
