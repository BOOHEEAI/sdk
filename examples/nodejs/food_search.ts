/**
 * 食物检索示例
 *
 * 用法:
 *   npx tsx food_search.ts                    # 默认搜索"苹果"
 *   npx tsx food_search.ts 米饭               # 按关键词搜索
 *   npx tsx food_search.ts --barcode 6901236  # 按条码搜索
 *   npx tsx food_search.ts 苹果 --sort calorie_asc --with-units
 */
import * as fs from 'fs';
import * as path from 'path';
import { BooheeClient, AuthMode, HttpMethod, Request } from '../../nodejs/src';

const HEALTH_LIGHT: Record<number, string> = {
  0: '无', 1: '🟢绿灯', 2: '🟡黄灯', 3: '🔴红灯',
};

class FoodSearchReq implements Request {
  private params: Record<string, any>;

  constructor(opts: {
    keyword?: string; barcode?: string; page?: number;
    perPage?: number; sort?: string; withUnits?: boolean;
  }) {
    this.params = {
      page: opts.page ?? 1,
      per_page: opts.perPage ?? 20,
    };
    if (opts.keyword) this.params.keyword = opts.keyword;
    if (opts.barcode) this.params.barcode = opts.barcode;
    if (opts.sort) this.params.sort = opts.sort;
    if (opts.withUnits) this.params.with_units = 'true';
  }

  getMethod() { return HttpMethod.GET; }
  getUrl() { return '/open-apis/v1/food/search'; }
  getQueryParams() { return this.params; }
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
  keyword?: string; barcode?: string; sort?: string;
  page: number; perPage: number; withUnits: boolean;
} {
  const opts = { page: 1, perPage: 20, withUnits: false } as any;
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--barcode': opts.barcode = args[++i]; break;
      case '--sort': opts.sort = args[++i]; break;
      case '--with-units': opts.withUnits = true; break;
      case '--page': opts.page = parseInt(args[++i]); break;
      case '--per-page': opts.perPage = parseInt(args[++i]); break;
      default: if (!opts.keyword) opts.keyword = args[i]; break;
    }
  }
  return opts;
}

async function main(): Promise<void> {
  loadEnv();

  const appId = process.env.BOOHEE_APP_ID;
  const appKey = process.env.BOOHEE_APP_KEY;
  const privateKeyPath = process.env.BOOHEE_PRIVATE_KEY_PATH;
  if (!appId || !appKey || !privateKeyPath) {
    console.log('ACCESS_TOKEN 模式需要配置 BOOHEE_APP_ID, BOOHEE_APP_KEY, BOOHEE_PRIVATE_KEY_PATH');
    process.exit(1);
  }

  const privateKey = fs.readFileSync(privateKeyPath, 'utf-8');

  const client = new BooheeClient({
    appId,
    appKey,
    privateKey,
    authMode: AuthMode.ACCESS_TOKEN,
    baseUrl: process.env.BOOHEE_BASE_URL || 'https://api.boohee.com',
  });

  const opts = parseArgs();
  if (!opts.keyword && !opts.barcode) opts.keyword = '苹果';
  if (opts.keyword && opts.barcode) {
    console.log('keyword 和 barcode 二选一，不能同时传入');
    process.exit(1);
  }

  const label = opts.keyword || opts.barcode;
  console.log(`搜索: ${label}\n`);

  const resp = await client.execute(new FoodSearchReq(opts));
  resp.raiseForError();

  const data = resp.data ?? {};
  const foods: any[] = data.foods ?? [];

  for (const food of foods) {
    const light = HEALTH_LIGHT[food.health_light ?? 0] ?? '无';
    const liquid = food.is_liquid ? ' [液体]' : '';
    console.log(`  ${food.name ?? '?'}${liquid}  ${light}`);
    console.log(`    热量: ${food.calories ?? '?'}kcal  ` +
      `蛋白质: ${food.protein ?? '?'}g  ` +
      `脂肪: ${food.fat ?? '?'}g  ` +
      `碳水: ${food.carbohydrate ?? '?'}g`);
    if (food.image_url) {
      console.log(`    图片: ${food.image_url}`);
    }
    if (food.units?.length) {
      const unitStrs = food.units.slice(0, 3)
        .map((u: any) => `${u.unit_name}(${u.weight}g)`);
      console.log(`    常用单位: ${unitStrs.join(', ')}`);
    }
    console.log();
  }

  const page = data.page ?? 1;
  const perPage = data.per_page ?? 20;
  const hasMore = data.has_more ?? false;
  console.log(`第 ${page} 页, 每页 ${perPage} 条, 共 ${foods.length} 条` +
    (hasMore ? '  有下一页' : ''));
}

main().catch(console.error);
