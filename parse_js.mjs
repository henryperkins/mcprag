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
  const functions = [];
  const classes = [];

  traverse.default(ast, {
    ImportDeclaration(path) { 
      if (path.node.source?.value) {
        // Include specific imports if available
        const specifiers = path.node.specifiers.map(s => {
          if (s.type === "ImportDefaultSpecifier") return s.local.name;
          if (s.type === "ImportSpecifier") return s.imported.name;
          return null;
        }).filter(Boolean);
        
        if (specifiers.length > 0) {
          specifiers.forEach(spec => imports.add(`${path.node.source.value}.${spec}`));
        } else {
          imports.add(path.node.source.value);
        }
      }
    },
    
    FunctionDeclaration(path) { 
      if (path.node.id?.name) {
        const params = path.node.params.map(p => {
          if (p.type === "Identifier") return p.name;
          if (p.type === "ObjectPattern") return "{}";
          if (p.type === "ArrayPattern") return "[]";
          return "...";
        });
        
        functions.push({
          name: path.node.id.name,
          params: params,
          async: path.node.async,
          generator: path.node.generator,
          start: path.node.loc?.start.line,
          end: path.node.loc?.end.line
        });
      }
    },
    
    ArrowFunctionExpression(path) {
      // Try to get the variable name if it's assigned
      const parent = path.parent;
      if (parent.type === "VariableDeclarator" && parent.id?.name) {
        const params = path.node.params.map(p => {
          if (p.type === "Identifier") return p.name;
          if (p.type === "ObjectPattern") return "{}";
          if (p.type === "ArrayPattern") return "[]";
          return "...";
        });
        
        functions.push({
          name: parent.id.name,
          params: params,
          async: path.node.async,
          arrow: true,
          start: path.node.loc?.start.line,
          end: path.node.loc?.end.line
        });
      }
    },
    
    ClassDeclaration(path) {
      if (path.node.id?.name) {
        const superClass = path.node.superClass?.name || null;
        classes.push({
          name: path.node.id.name,
          extends: superClass,
          start: path.node.loc?.start.line,
          end: path.node.loc?.end.line
        });
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

  // Create chunks for each function and class
  const chunks = [];
  
  // Add function chunks
  for (const func of functions) {
    const signature = func.arrow 
      ? `const ${func.name} = ${func.async ? 'async ' : ''}(${func.params.join(', ')}) => ...`
      : `${func.async ? 'async ' : ''}${func.generator ? 'function* ' : 'function '}${func.name}(${func.params.join(', ')})`;
    
    chunks.push({
      type: "function",
      name: func.name,
      signature: signature,
      start_line: func.start,
      end_line: func.end
    });
  }
  
  // Add class chunks
  for (const cls of classes) {
    const signature = cls.extends 
      ? `class ${cls.name} extends ${cls.extends}`
      : `class ${cls.name}`;
      
    chunks.push({
      type: "class",
      name: cls.name,
      signature: signature,
      start_line: cls.start,
      end_line: cls.end
    });
  }
  
  // Sort chunks by start line
  chunks.sort((a, b) => (a.start_line || 0) - (b.start_line || 0));

  const result = {
    chunks: chunks,
    imports_used: [...imports],
    calls_functions: [...calls]
  };

  console.log(JSON.stringify(result));

} catch (error) {
  // Return empty result on parse error
  console.log(JSON.stringify({
    chunks: [],
    imports_used: [],
    calls_functions: []
  }));
}
