export function parseTextVisibility(canvasImgData, texts) {
  var data = canvasImgData.data,
    width = canvasImgData.width,
    height = canvasImgData.height,
    defaultColor = [0, 0, 0],
    minVariance = 20;

  texts.forEach(function (t) {
    var left = Math.floor(t.transform[4]),
      w = Math.round(t.width),
      h = Math.round(t.height),
      bottom = Math.round(height - t.transform[5]),
      top = bottom - h,
      start = (left + top * width) * 4,
      // color = [],
      // best = Infinity,
      stat = new ImageStats();

    for (var i, v, row = 0; row < h; row++) {
      i = start + row * width * 4;
      for (var col = 0; col < w; col++) {
        // if ((v = data[i] + data[i + 1] + data[i + 2]) < best) {
        //   // the darker the "better"
        //   best = v;
        //   color[0] = data[i];
        //   color[1] = data[i + 1];
        //   color[2] = data[i + 2];
        // }
        stat.addPixel(data[i], data[i + 1], data[i + 2]);
        i += 4;
      }
    }
    // var stdDev = stat.getStdDev();
    // t.color = stdDev < minVariance ? defaultColor : color;
    const uniqueColors = stat.getUniqueColors();
    console.log(`${t.str}: uniqueColors: ${uniqueColors}`);
    t.textInvisible = uniqueColors < 2;
  });
}

class ImageStats {
  constructor() {
    this.pixelCount = 0;
    this.pixels = [];
    this.rgb = [];
    this.mean = 0;
    this.stdDev = 0;
  }
  addPixel(r, g, b) {
    if (!this.rgb.length) {
      this.rgb[0] = r;
      this.rgb[1] = g;
      this.rgb[2] = b;
    } else {
      this.rgb[0] += r;
      this.rgb[1] += g;
      this.rgb[2] += b;
    }
    this.pixelCount++;
    this.pixels.push([r, g, b]);
  }

 
  getUniqueColors() {
    const uniqueColors = new Set();
    this.pixels.forEach(([r, g, b]) => {
      uniqueColors.add(`${r},${g},${b}`);
    });
    console.log(`uniqueColors: ${JSON.stringify([...uniqueColors.values()])}`);
    return uniqueColors.size;
  }
}
