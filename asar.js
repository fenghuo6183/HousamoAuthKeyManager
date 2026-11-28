const fs = require('fs');
const path = require('path');

const asarPath = process.argv[2];
const cmd = process.argv[3] || 'list';
const needle = process.argv[4] || '';
const outDir = process.argv[5] || './asar-out';

const fd = fs.openSync(asarPath, 'r');
const head = Buffer.alloc(16);
fs.readSync(fd, head, 0, 16, 0);
const headerSize = head.readUInt32LE(4); // size pickle payload == header pickle total size
const headerBuf = Buffer.alloc(headerSize);
fs.readSync(fd, headerBuf, 0, headerSize, 8);
// header pickle: [u32 payloadSize][u32 stringLen][json...]
const jsonLen = headerBuf.readUInt32LE(4);
const json = headerBuf.slice(8, 8 + jsonLen).toString('utf8');
const header = JSON.parse(json);
const base = 8 + headerSize;

const entries = [];
function walk(node, prefix) {
  for (const [name, item] of Object.entries(node.files || {})) {
    const p = prefix ? prefix + '/' + name : name;
    if (item.files) walk(item, p);
    else entries.push({ path: p, offset: Number(item.offset), size: item.size });
  }
}
walk(header, '');

if (cmd === 'list') {
  const hits = entries.filter(e => !needle || e.path.toLowerCase().includes(needle.toLowerCase()));
  console.log('total files:', entries.length, '| matches:', hits.length);
  for (const h of hits.slice(0, 300)) console.log(h.size + '\t' + h.path);
  process.exit(0);
}

if (cmd === 'extract') {
  const hits = entries.filter(e => needle2(e.path));
  function needle2(p) { return p.includes(needle); }
  console.log('extracting', hits.length, 'files');
  for (const h of hits) {
    const target = path.join(outDir, h.path.replace(/[:*?"<>|]/g, '_'));
    fs.mkdirSync(path.dirname(target), { recursive: true });
    const buf = Buffer.alloc(h.size);
    fs.readSync(fd, buf, 0, h.size, base + h.offset);
    fs.writeFileSync(target, buf);
    console.log('wrote', target, h.size);
  }
}
fs.closeSync(fd);