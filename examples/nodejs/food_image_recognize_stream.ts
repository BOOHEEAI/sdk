/**
 * 流式图片识别示例
 *
 * 用法:
 *   npx tsx food_image_recognize_stream.ts                              # 默认图片
 *   npx tsx food_image_recognize_stream.ts --url https://xxx.jpg        # 按URL识别
 *   npx tsx food_image_recognize_stream.ts --base64 /path/to/image.jpg  # 按base64识别
 *   npx tsx food_image_recognize_stream.ts --url https://xxx.jpg --ingredients sugar,purine --with-nrv
 */
import * as fs from 'fs';
import * as path from 'path';
import { BooheeClient, AuthMode, HttpMethod, Request } from '../../nodejs/src';

class FoodImageRecognizeStreamReq implements Request {
  private body: Record<string, any>;

  constructor(opts: {
    imageUrl?: string; imageData?: string;
    ingredients?: string; withNrv?: boolean;
  }) {
    this.body = {};
    if (opts.imageUrl) this.body.image_url = opts.imageUrl;
    if (opts.imageData) this.body.image_data = opts.imageData;
    if (opts.ingredients) this.body.ingredients = opts.ingredients;
    if (opts.withNrv) this.body.with_nrv = true;
  }

  getMethod() { return HttpMethod.POST; }
  getUrl() { return '/open-apis/v1/food/image_recongize_stream'; }
  getBody() { return this.body; }
}

function loadEnv(): void {
  const envPath = path.resolve(__dirname, '../../.env');
  if (!fs.existsSync(envPath)) {
    console.log('请先复制 .env.example 为 .env 并填入真实凭证');
    process.exit(1);
  }
  const content = fs.readFileSync(envPath, 'utf-8');
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx > 0) {
      const key = trimmed.substring(0, idx).trim();
      const value = trimmed.substring(idx + 1).trim();
      if (!process.env[key]) {
        process.env[key] = value;
      }
    }
  }
}

function parseArgs(): {
  imageUrl?: string; imageData?: string;
  ingredients?: string; withNrv: boolean;
} {
  const opts = { withNrv: false } as any;
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--url': opts.imageUrl = args[++i]; break;
      case '--base64':
        const fileBytes = fs.readFileSync(args[++i]);
        opts.imageData = fileBytes.toString('base64');
        break;
      case '--ingredients': opts.ingredients = args[++i]; break;
      case '--with-nrv': opts.withNrv = true; break;
    }
  }
  return opts;
}

async function main(): Promise<void> {
  loadEnv();

  const apiKey = process.env.BOOHEE_API_KEY;
  if (!apiKey) {
    console.log('BOOHEE_API_KEY 未配置');
    process.exit(1);
  }

  const client = new BooheeClient({
    authMode: AuthMode.API_KEY,
    apiKey,
    baseUrl: process.env.BOOHEE_BASE_URL || 'https://api.boohee.com',
  });

  const opts = parseArgs();
  if (!opts.imageUrl && !opts.imageData) {
    opts.imageUrl = 'https://img.boohee.cn/ghp/foods/000/000/001/140_1.jpg';
  }

  const label = opts.imageUrl || 'base64数据';
  console.log(`识别图片: ${label}\n`);
  console.log('流式输出:');

  let fullContent = '';
  let foodInfo: any[] = [];

  for await (const chunk of client.executeStream(new FoodImageRecognizeStreamReq(opts))) {
    try {
      const event = JSON.parse(chunk);
      if (event.result_code !== 0) {
        console.log(`\n错误: ${event.message}`);
        process.exit(1);
      }
      const data = event.data ?? {};
      if (data.content) {
        process.stdout.write(data.content);
        fullContent += data.content;
      }
      if (data.end) {
        foodInfo = data.food_info ?? [];
      }
    } catch {
      // 忽略解析错误
    }
  }

  console.log();

  if (foodInfo.length > 0) {
    console.log(`\n--- 识别到 ${foodInfo.length} 个食物 ---\n`);
    for (const food of foodInfo) {
      console.log(`  ${food.name ?? '?'}  估重: ${food.amount ?? '?'}g  ` +
        `热量: ${food.calories ?? '?'}kcal/100g  ` +
        `蛋白质: ${food.protein ?? '?'}g  ` +
        `脂肪: ${food.fat ?? '?'}g  ` +
        `碳水: ${food.carbohydrate ?? '?'}g`);
      if (food.ingredients?.length) {
        const ingStrs = food.ingredients.map(
          (i: any) => `${i.name}: ${i.value}${i.unit}`);
        console.log(`    营养素: ${ingStrs.join(', ')}`);
      }
      if (food.nrv?.length) {
        const nrvStrs = food.nrv.map(
          (n: any) => `${n.name}: ${n.value}`);
        console.log(`    NRV: ${nrvStrs.join(', ')}`);
      }
      console.log();
    }
  }
}

main().catch(console.error);
