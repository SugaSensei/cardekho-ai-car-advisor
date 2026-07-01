import assert from 'assert';

// Mock React structures for parsing test in pure Node
const mockRenderMessageText = (text) => {
  if (!text) return null;
  const lines = text.split('\n');
  return lines.map((line, lineIdx) => {
    const headerMatch = line.match(/^(#{1,6})\s+(.*)/);
    let content = line;
    let isHeader = false;
    let headerLevel = 0;
    
    if (headerMatch) {
      content = headerMatch[2];
      isHeader = true;
      headerLevel = headerMatch[1].length;
    }
    
    if (!isHeader) {
      content = content.replace(/^([ \t]*)[*-]\s+/, '$1• ');
    }
    
    const parseInline = (textSegment) => {
      const boldParts = textSegment.split(/(\*\*[^*]+\*\*)/g);
      return boldParts.map((boldPart) => {
        if (boldPart.startsWith('**') && boldPart.endsWith('**')) {
          return { type: 'strong', content: boldPart.slice(2, -2) };
        }
        
        const codeParts = boldPart.split(/(\`[^`]+\`)/g);
        return codeParts.map((codePart) => {
          if (codePart.startsWith('`') && codePart.endsWith('`')) {
            return { type: 'code', content: codePart.slice(1, -1) };
          }
          
          const italicParts = codePart.split(/(\*[^*]+\*)/g);
          return italicParts.map((italicPart) => {
            if (italicPart.startsWith('*') && italicPart.endsWith('*')) {
              return { type: 'em', content: italicPart.slice(1, -1) };
            }
            return { type: 'text', content: italicPart };
          });
        });
      });
    };
    
    return {
      lineIdx,
      isHeader,
      headerLevel,
      parsedContent: parseInline(content)
    };
  });
};

// -------------------------
// TEST CASES
// -------------------------
console.log("Starting Markdown Parser Frontend Tests...");

// Test Case 1: H6 Header Matching
const res1 = mockRenderMessageText("###### Great Choices for Your Summer Family Drives!");
assert.strictEqual(res1[0].isHeader, true);
assert.strictEqual(res1[0].headerLevel, 6);
const flatContent1 = res1[0].parsedContent.flat(3);
assert.strictEqual(flatContent1[0].type, 'text');
assert.strictEqual(flatContent1[0].content, 'Great Choices for Your Summer Family Drives!');
console.log("✅ H6 Header matched and parsed successfully.");

// Test Case 2: H1-H3 Headers
const res2 = mockRenderMessageText("# Main Title\n## Sub Title\n### Small Title");
assert.strictEqual(res2[0].headerLevel, 1);
assert.strictEqual(res2[1].headerLevel, 2);
assert.strictEqual(res2[2].headerLevel, 3);
console.log("✅ H1, H2, and H3 Header levels parsed successfully.");

// Test Case 3: Bullet points normalization
const res3 = mockRenderMessageText("* Item 1\n  - Item 2");
const flatContent3_1 = res3[0].parsedContent.flat(3);
const flatContent3_2 = res3[1].parsedContent.flat(3);
assert.strictEqual(flatContent3_1[0].content, '• Item 1');
assert.strictEqual(flatContent3_2[0].content, '  • Item 2');
console.log("✅ List item normalization parsed successfully.");

// Test Case 4: Inline formatting (bold, italic, code)
const res4 = mockRenderMessageText("This is **bold** text and `code` with *italic*.");
const flatContent4 = res4[0].parsedContent.flat(3);
assert.strictEqual(flatContent4[0].content, 'This is ');
assert.strictEqual(flatContent4[1].type, 'strong');
assert.strictEqual(flatContent4[1].content, 'bold');
assert.strictEqual(flatContent4[2].content, ' text and ');
assert.strictEqual(flatContent4[3].type, 'code');
assert.strictEqual(flatContent4[3].content, 'code');
assert.strictEqual(flatContent4[4].content, ' with ');
assert.strictEqual(flatContent4[5].type, 'em');
assert.strictEqual(flatContent4[5].content, 'italic');
console.log("✅ Inline styling (bold, code, italic) nested splits parsed successfully.");

console.log("🎉 All frontend parser tests passed successfully!");
