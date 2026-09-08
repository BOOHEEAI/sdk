#!/usr/bin/env python3
"""食物检索示例

用法:
  python food_search.py                    # 默认搜索"苹果"
  python food_search.py 米饭               # 按关键词搜索
  python food_search.py --barcode 6901236  # 按条码搜索
  python food_search.py 苹果 --sort calorie_asc --with-units
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../python'))

from boohee_sdk import BooheeClient, AuthMode, BaseReq, HttpMethod

HEALTH_LIGHT = {0: '无', 1: '🟢绿灯', 2: '🟡黄灯', 3: '🔴红灯'}


class FoodSearchReq(BaseReq):
    def __init__(self, keyword=None, barcode=None, page=1, per_page=20,
                 sort=None, with_units=False):
        self.keyword = keyword
        self.barcode = barcode
        self.page = page
        self.per_page = per_page
        self.sort = sort
        self.with_units = with_units

    def get_method(self) -> HttpMethod:
        return HttpMethod.GET

    def get_url(self) -> str:
        return '/open-apis/v1/food/search'

    def get_query_params(self):
        params = {'page': self.page, 'per_page': self.per_page}
        if self.keyword:
            params['keyword'] = self.keyword
        if self.barcode:
            params['barcode'] = self.barcode
        if self.sort:
            params['sort'] = self.sort
        if self.with_units:
            params['with_units'] = 'true'
        return params


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '../../.env')
    if not os.path.exists(env_path):
        print("请先复制 .env.example 为 .env 并填入真实凭证")
        sys.exit(1)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())


def parse_args():
    args = sys.argv[1:]
    opts = {'page': 1, 'per_page': 20}
    positional = []
    i = 0
    while i < len(args):
        if args[i] == '--barcode':
            opts['barcode'] = args[i + 1]; i += 2
        elif args[i] == '--sort':
            opts['sort'] = args[i + 1]; i += 2
        elif args[i] == '--with-units':
            opts['with_units'] = True; i += 1
        elif args[i] == '--page':
            opts['page'] = int(args[i + 1]); i += 2
        elif args[i] == '--per-page':
            opts['per_page'] = int(args[i + 1]); i += 2
        else:
            positional.append(args[i]); i += 1
    if positional:
        opts['keyword'] = positional[0]
    return opts


def main():
    load_env()

    # ACCESS_TOKEN 模式
    app_id = os.environ.get('BOOHEE_APP_ID')
    app_key = os.environ.get('BOOHEE_APP_KEY')
    private_key_path = os.environ.get('BOOHEE_PRIVATE_KEY_PATH')
    if not all([app_id, app_key, private_key_path]):
        print("ACCESS_TOKEN 模式需要配置 BOOHEE_APP_ID, BOOHEE_APP_KEY, BOOHEE_PRIVATE_KEY_PATH")
        sys.exit(1)

    with open(private_key_path) as f:
        private_key = f.read()

    client = BooheeClient(
        app_id=app_id,
        app_key=app_key,
        private_key=private_key,
        auth_mode=AuthMode.ACCESS_TOKEN,
        base_url=os.environ.get('BOOHEE_BASE_URL', 'https://api.boohee.com'),
    )
    opts = parse_args()

    if not opts.get('keyword') and not opts.get('barcode'):
        print("keyword 和 barcode 至少传入一个")
        sys.exit(1)

    label = opts.get('keyword') or opts.get('barcode')
    print(f"搜索: {label}\n")

    resp = client.execute(FoodSearchReq(**opts))
    resp.raise_for_error()

    data = resp.data or {}
    foods = data.get('foods', [])
    page = data.get('page', 1)
    per_page = data.get('per_page', 20)
    has_more = data.get('has_more', False)

    for food in foods:
        light = HEALTH_LIGHT.get(food.get('health_light', 0), '无')
        liquid = ' [液体]' if food.get('is_liquid') else ''
        print(f"  {food.get('name', '?')}{liquid}  {light}")
        print(f"    热量: {food.get('calories', '?')}kcal  "
              f"蛋白质: {food.get('protein', '?')}g  "
              f"脂肪: {food.get('fat', '?')}g  "
              f"碳水: {food.get('carbohydrate', '?')}g")
        if food.get('image_url'):
            print(f"    图片: {food['image_url']}")
        units = food.get('units', [])
        if units:
            unit_strs = [f"{u['unit_name']}({u['weight']}g)" for u in units[:3]]
            print(f"    常用单位: {', '.join(unit_strs)}")
        print()

    print(f"第 {page} 页, 每页 {per_page} 条, 共 {len(foods)} 条"
          f"{'  有下一页' if has_more else ''}")


if __name__ == '__main__':
    main()
