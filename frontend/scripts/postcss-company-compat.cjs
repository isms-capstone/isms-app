// GET Design 1.0.7 emits six debug alias declarations such as
// --border-brand-subtle-ref: var("brand-alpha-light-32"). Quoted var() arguments
// are invalid CSS and rejected by Next/Turbopack. None are used by components.
// Drop only that invalid metadata in the company's stylesheet; preserve all real
// tokens/component rules and never edit node_modules or unrelated project CSS.
module.exports = function companyCssCompat() {
  return {
    postcssPlugin: "isms-get-design-css-compat",
    Once(root) {
      const source = (root.source?.input.file || "").replaceAll("\\", "/");
      if (!source.includes("/@DeverhoodHT/get-design/")) return;
      root.walkDecls((declaration) => {
        if (
          declaration.prop.endsWith("-ref") &&
          /^var\(\s*["'][^"']+["']\s*\)$/.test(declaration.value)
        )
          declaration.remove();
      });
    },
  };
};
module.exports.postcss = true;
