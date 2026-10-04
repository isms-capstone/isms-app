module.exports = {
  root: true,
  env: {browser: true, es2022: true},
  parserOptions: {ecmaVersion: 'latest', sourceType: 'module'},
  extends: ['eslint:recommended'],
  overrides: [{files: ['*.cjs'], env: {node: true}, parserOptions: {sourceType: 'script'}}],
};
