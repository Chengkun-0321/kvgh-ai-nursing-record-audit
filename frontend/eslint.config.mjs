import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      "@typescript-eslint/no-explicit-any": "error",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "max-params": ["error", 4],
      "max-depth": ["error", 2],
      complexity: ["error", 8],
      "max-lines": [
        "error",
        { max: 300, skipBlankLines: true, skipComments: true },
      ],
    },
  },
  {
    files: ["src/components/**/*.tsx", "src/app/**/*.tsx"],
    rules: {
      "max-lines-per-function": [
        "error",
        { max: 150, skipBlankLines: true, skipComments: true },
      ],
    },
  },
  {
    files: ["src/lib/**/*.ts", "src/hooks/**/*.ts"],
    rules: {
      "max-lines-per-function": [
        "error",
        { max: 30, skipBlankLines: true, skipComments: true },
      ],
    },
  },
  globalIgnores([
    ".next/**",
    "out/**",
    "build/**",
    ".npm-cache/**",
    "next-env.d.ts",
    "src/types/api.ts",
  ]),
]);

export default eslintConfig;
