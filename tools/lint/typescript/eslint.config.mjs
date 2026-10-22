import js from "../../../third_party/npm/node_modules/@eslint/js/src/index.js";
import tseslint from "../../../third_party/npm/node_modules/typescript-eslint/dist/index.js";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
);
