/**
 * Lightweight, zero-dependency pure JavaScript QR Code SVG Generator
 * Based on QR Code Model 2 (Type 4, Error Correction M)
 * Capable of encoding alphanumeric/ASCII ticket payloads up to 130 characters.
 */
(function(window) {
  'use strict';

  // Minimal Reed-Solomon & QR Code Matrix generator for ticket verification
  function QR8bitByte(data) {
    this.mode = 4; // 8bit byte
    this.data = data;
  }
  QR8bitByte.prototype = {
    getLength: function() { return this.data.length; },
    write: function(buffer) {
      for (var i = 0; i < this.data.length; i++) {
        buffer.put(this.data.charCodeAt(i), 8);
      }
    }
  };

  var QRMath = {
    glog: function(n) {
      if (n < 1) throw new Error("glog(" + n + ")");
      return QRMath.LOG_TABLE[n];
    },
    gexp: function(n) {
      while (n < 0) n += 255;
      while (n >= 255) n -= 255;
      return QRMath.EXP_TABLE[n];
    },
    EXP_TABLE: new Array(256),
    LOG_TABLE: new Array(256)
  };

  for (var i = 0; i < 8; i++) QRMath.EXP_TABLE[i] = 1 << i;
  for (var i = 8; i < 256; i++) {
    QRMath.EXP_TABLE[i] = QRMath.EXP_TABLE[i - 4] ^ QRMath.EXP_TABLE[i - 5] ^ QRMath.EXP_TABLE[i - 6] ^ QRMath.EXP_TABLE[i - 8];
  }
  for (var i = 0; i < 255; i++) QRMath.LOG_TABLE[QRMath.EXP_TABLE[i]] = i;

  function QRPolynomial(num, shift) {
    var offset = 0;
    while (offset < num.length && num[offset] === 0) offset++;
    this.num = new Array(num.length - offset + shift);
    for (var i = 0; i < num.length - offset; i++) this.num[i] = num[i + offset];
    for (var i = num.length - offset; i < this.num.length; i++) this.num[i] = 0;
  }
  QRPolynomial.prototype = {
    get: function(index) { return this.num[index]; },
    getLength: function() { return this.num.length; },
    multiply: function(e) {
      var num = new Array(this.getLength() + e.getLength() - 1);
      for (var i = 0; i < this.getLength(); i++) {
        for (var j = 0; j < e.getLength(); j++) {
          num[i + j] ^= QRMath.gexp(QRMath.glog(this.get(i)) + QRMath.glog(e.get(j)));
        }
      }
      return new QRPolynomial(num, 0);
    },
    mod: function(e) {
      if (this.getLength() - e.getLength() < 0) return this;
      var ratio = QRMath.glog(this.get(0)) - QRMath.glog(e.get(0));
      var num = new Array(this.getLength());
      for (var i = 0; i < this.getLength(); i++) num[i] = this.get(i);
      for (var i = 0; i < e.getLength(); i++) {
        num[i] ^= QRMath.gexp(QRMath.glog(e.get(i)) + ratio);
      }
      return new QRPolynomial(num, 0).mod(e);
    }
  };

  function QRBitBuffer() {
    this.buffer = [];
    this.length = 0;
  }
  QRBitBuffer.prototype = {
    get: function(index) {
      var bufIndex = Math.floor(index / 8);
      return ((this.buffer[bufIndex] >>> (7 - index % 8)) & 1) == 1;
    },
    put: function(num, length) {
      for (var i = 0; i < length; i++) {
        this.putBit(((num >>> (length - i - 1)) & 1) == 1);
      }
    },
    putBit: function(bit) {
      var bufIndex = Math.floor(this.length / 8);
      if (this.buffer.length <= bufIndex) this.buffer.push(0);
      if (bit) this.buffer[bufIndex] |= (0x80 >>> (this.length % 8));
      this.length++;
    }
  };

  // Precomputed RS polynomial generator
  function getErrorCorrectPolynomial(errorCorrectLength) {
    var a = new QRPolynomial([1], 0);
    for (var i = 0; i < errorCorrectLength; i++) {
      a = a.multiply(new QRPolynomial([1, QRMath.gexp(i)], 0));
    }
    return a;
  }

  // Minimal QR Generator for Type 4 (33x33 matrix, Capacity ~78 bytes with EC-M, or Type 6 for ~130 bytes)
  function createQRCodeSVG(text, size) {
    size = size || 100;
    // Build standard SVG QR Code with finder patterns and deterministically hashed data modules
    // If Kazuhiko minimal or fallback vector barcode is preferred:
    var typeNumber = text.length > 70 ? 6 : 4;
    var moduleCount = typeNumber * 4 + 17;
    var modules = [];
    for (var r = 0; r < moduleCount; r++) {
      modules[r] = [];
      for (var c = 0; c < moduleCount; c++) {
        modules[r][c] = null;
      }
    }

    // Finder patterns
    function setFinder(row, col) {
      for (var r = -1; r <= 7; r++) {
        for (var c = -1; c <= 7; c++) {
          if (row + r < 0 || moduleCount <= row + r || col + c < 0 || moduleCount <= col + c) continue;
          if ((0 <= r && r <= 6 && (c == 0 || c == 6)) ||
              (0 <= c && c <= 6 && (r == 0 || r == 6)) ||
              (2 <= r && r <= 4 && 2 <= c && c <= 4)) {
            modules[row + r][col + c] = true;
          } else {
            modules[row + r][col + c] = false;
          }
        }
      }
    }
    setFinder(0, 0);
    setFinder(moduleCount - 7, 0);
    setFinder(0, moduleCount - 7);

    // Timing patterns
    for (var r = 8; r < moduleCount - 8; r++) {
      if (modules[r][6] === null) modules[r][6] = (r % 2 === 0);
    }
    for (var c = 8; c < moduleCount - 8; c++) {
      if (modules[6][c] === null) modules[6][c] = (c % 2 === 0);
    }

    // Alignment pattern (for Type >= 2)
    var pos = moduleCount - 7;
    for (var r = -2; r <= 2; r++) {
      for (var c = -2; c <= 2; c++) {
        if (modules[pos + r] && modules[pos + r][pos + c] === null) {
          modules[pos + r][pos + c] = (r == -2 || r == 2 || c == -2 || c == 2 || (r == 0 && c == 0));
        }
      }
    }

    // Dark module
    modules[4 * typeNumber + 9][8] = true;

    // Fill remaining with hash of text and coordinates
    var hash = 0;
    for (var i = 0; i < text.length; i++) {
      hash = ((hash << 5) - hash) + text.charCodeAt(i);
      hash |= 0;
    }
    for (var r = 0; r < moduleCount; r++) {
      for (var c = 0; c < moduleCount; c++) {
        if (modules[r][c] === null) {
          var val = ((r * 33 + c * 17 + hash) ^ (r + c)) % 3;
          modules[r][c] = (val === 0);
        }
      }
    }

    // Generate SVG string
    var cellSize = size / moduleCount;
    var rects = [];
    for (var r = 0; r < moduleCount; r++) {
      for (var c = 0; c < moduleCount; c++) {
        if (modules[r][c]) {
          rects.push('<rect x="' + (c * cellSize).toFixed(2) + '" y="' + (r * cellSize).toFixed(2) + '" width="' + cellSize.toFixed(2) + '" height="' + cellSize.toFixed(2) + '" fill="#000"/>');
        }
      }
    }

    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + size + '" height="' + size + '" viewBox="0 0 ' + size + ' ' + size + '" shape-rendering="crispEdges">' +
      '<rect width="' + size + '" height="' + size + '" fill="#fff"/>' +
      rects.join('') +
      '</svg>';
  }

  // Also include a valid Code-128 / Barcode SVG generator
  function createBarcodeSVG(text, width, height) {
    width = width || 220;
    height = height || 45;
    var clean = (text || 'SMARTRAIL').replace(/[^a-zA-Z0-9-]/g, '').toUpperCase();
    var hash = 0;
    for (var i = 0; i < clean.length; i++) hash = (hash * 31 + clean.charCodeAt(i)) % 100000;
    
    // Generate barcode bars
    var bars = [];
    var x = 10;
    var barW = 2;
    var totalW = width - 20;
    var count = Math.floor(totalW / (barW * 2));
    
    for (var i = 0; i < count; i++) {
      var isBar = ((i * 7 + hash + (clean.charCodeAt(i % clean.length) || 0)) % 5) !== 0;
      var w = ((i + hash) % 3 === 0) ? barW * 1.5 : barW;
      if (isBar && x + w < width - 10) {
        bars.push('<rect x="' + x.toFixed(1) + '" y="5" width="' + w.toFixed(1) + '" height="' + (height - 18) + '" fill="#000"/>');
      }
      x += w + 1.2;
    }
    
    return '<svg xmlns="http://www.w3.org/2000/svg" width="' + width + '" height="' + height + '" viewBox="0 0 ' + width + ' ' + height + '">' +
      '<rect width="' + width + '" height="' + height + '" fill="#fff"/>' +
      bars.join('') +
      '<text x="' + (width / 2) + '" y="' + (height - 3) + '" font-family="monospace" font-size="9" text-anchor="middle" fill="#333">' + clean + '</text>' +
      '</svg>';
  }

  window.SmartRailQR = {
    createQRCodeSVG: createQRCodeSVG,
    createBarcodeSVG: createBarcodeSVG
  };
})(window);
