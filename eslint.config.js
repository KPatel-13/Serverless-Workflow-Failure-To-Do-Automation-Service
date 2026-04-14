import globals from "globals";

export default [
  {
    files: ["frontend/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        ...globals.browser,
        API_BASE_URL: "readonly"
      }
    },
    rules: {
      "no-unused-vars": "error",
      "no-undef": "error"
    }
  }
];