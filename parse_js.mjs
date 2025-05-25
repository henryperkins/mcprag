#!/usr/bin/env node
import { readFileSync } from "fs";
import parser from "@babel/parser";
import traverse from "@babel/traverse";

const file = process.argv[2];
if (!file) {
  console.error("Usage: node parse_js.mjs <file>");
  process.exit(1);
}

try {
  const code = readFileSync(file, "utf8");

  const ast = parser.parse(code, {
    sourceType: "module",
    plugins: [
      "typescript", 
      "jsx", 
      "classProperties",
      "decorators-legacy",
      "asyncGenerators",
      "functionBind",
      "exportDefaultFrom",
      "exportNamespaceFrom",
      "dynamicImport",
      "nullishCoalescingOperator",
      "optionalChaining"
    ]
  });

  const imports = new Set();
  const calls = new Set();
  const funcs = [];
  const classes = [];

  traverse.default(ast, {
    ImportDeclaration(path) { 
      if (path.node.source?.value) {
        imports.add(path.node.source.value); 
      }
    },
    
    FunctionDeclaration(path) { 
      if (path.node.id?.name) {
        funcs.push(path.node.id.name);
      }
    },
    
    ArrowFunctionExpression(path) {
      // Try to get the variable name if it's assigned
      const parent = path.parent;
      if (parent.type === "VariableDeclarator" && parent.id?.name) {
        funcs.push(parent.id.name);
      }
    },
    
    ClassDeclaration(path) {
      if (path.node.id?.name) {
        classes.push(path.node.id.name);
      }
    },
    
    CallExpression(path) {
      if (path.node.callee.type === "Identifier") {
        calls.add(path.node.callee.name);
      } else if (path.node.callee.type === "MemberExpression" && 
                 path.node.callee.property?.name) {
        calls.add(path.node.callee.property.name);
      }
    }
  });

  // Create a meaningful function signature
  let signature = "";
  if (funcs.length > 0) {
    signature = `function ${funcs[0]}()`;
  } else if (classes.length > 0) {
    signature = `class ${classes[0]}`;
  }

  const result = {
    function_signature: signature,
    imports_used: [...imports],
    calls_functions: [...calls]
  };

  console.log(JSON.stringify(result));

} catch (error) {
  // Return empty result on parse error
  console.log(JSON.stringify({
    function_signature: "",
    imports_used: [],
    calls_functions: []
  }));
}
