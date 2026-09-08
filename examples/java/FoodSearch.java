import com.boohee.ai.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

/**
 * 食物检索示例
 *
 * 用法:
 *   java FoodSearch                    # 默认搜索"苹果"
 *   java FoodSearch 米饭               # 按关键词搜索
 *   java FoodSearch --barcode 6901236  # 按条码搜索
 *   java FoodSearch 苹果 --sort calorie_asc --with-units
 */
public class FoodSearch {

    static final Map<Integer, String> HEALTH_LIGHT = new HashMap<Integer, String>() {{
        put(0, "无"); put(1, "🟢绿灯"); put(2, "🟡黄灯"); put(3, "🔴红灯");
    }};

    static class FoodSearchReq implements BaseReq {
        private final Map<String, Object> params = new HashMap<>();

        FoodSearchReq(String keyword, String barcode, int page, int perPage,
                      String sort, boolean withUnits) {
            if (keyword != null) params.put("keyword", keyword);
            if (barcode != null) params.put("barcode", barcode);
            params.put("page", page);
            params.put("per_page", perPage);
            if (sort != null) params.put("sort", sort);
            if (withUnits) params.put("with_units", "true");
        }

        @Override public HttpMethod getMethod() { return HttpMethod.GET; }
        @Override public String getUrl() { return "/open-apis/v1/food/search"; }
        @Override public Map<String, Object> getQueryParams() { return params; }
    }

    static void loadEnv() throws IOException {
        Path envPath = Paths.get(".env");
        if (!Files.exists(envPath)) {
            System.out.println("请先复制 .env.example 为 .env 并填入真实凭证");
            System.exit(1);
        }
        for (String line : Files.readAllLines(envPath)) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            int idx = line.indexOf('=');
            if (idx > 0) {
                String key = line.substring(0, idx).trim();
                String value = line.substring(idx + 1).trim();
                if (System.getenv(key) == null) {
                    System.setProperty(key, value);
                }
            }
        }
    }

    @SuppressWarnings("unchecked")
    public static void main(String[] args) throws Exception {
        loadEnv();

        String appId = System.getProperty("BOOHEE_APP_ID", System.getenv("BOOHEE_APP_ID"));
        String appKey = System.getProperty("BOOHEE_APP_KEY", System.getenv("BOOHEE_APP_KEY"));
        String privateKeyPath = System.getProperty("BOOHEE_PRIVATE_KEY_PATH", System.getenv("BOOHEE_PRIVATE_KEY_PATH"));
        if (appId == null || appId.isEmpty() || appKey == null || appKey.isEmpty()
                || privateKeyPath == null || privateKeyPath.isEmpty()) {
            System.out.println("ACCESS_TOKEN 模式需要配置 BOOHEE_APP_ID, BOOHEE_APP_KEY, BOOHEE_PRIVATE_KEY_PATH");
            System.exit(1);
        }

        String privateKey = new String(Files.readAllBytes(Paths.get(privateKeyPath)));
        String baseURL = System.getProperty("BOOHEE_BASE_URL",
                System.getenv().getOrDefault("BOOHEE_BASE_URL", "https://api.boohee.com"));

        BooheeClient client = BooheeClient.builder()
                .appId(appId)
                .appKey(appKey)
                .privateKey(privateKey)
                .baseURL(baseURL)
                .build();

        // 解析参数
        String keyword = null, barcode = null, sort = null;
        int page = 1, perPage = 20;
        boolean withUnits = false;
        for (int i = 0; i < args.length; i++) {
            switch (args[i]) {
                case "--barcode": barcode = args[++i]; break;
                case "--sort": sort = args[++i]; break;
                case "--with-units": withUnits = true; break;
                case "--page": page = Integer.parseInt(args[++i]); break;
                case "--per-page": perPage = Integer.parseInt(args[++i]); break;
                default: if (keyword == null) keyword = args[i]; break;
            }
        }
        if (keyword == null && barcode == null) keyword = "苹果";
        if (keyword != null && barcode != null) {
            System.out.println("keyword 和 barcode 二选一，不能同时传入");
            System.exit(1);
        }

        String label = keyword != null ? keyword : barcode;
        System.out.println("搜索: " + label + "\n");

        BaseResp resp = client.execute(new FoodSearchReq(keyword, barcode, page, perPage, sort, withUnits));
        resp.raiseForError();

        Map<String, Object> data = resp.getData();
        if (data == null) return;

        List<Map<String, Object>> foods = (List<Map<String, Object>>) data.get("foods");
        if (foods != null) {
            for (Map<String, Object> food : foods) {
                String name = (String) food.getOrDefault("name", "?");
                int hl = food.get("health_light") instanceof Number
                        ? ((Number) food.get("health_light")).intValue() : 0;
                String light = HEALTH_LIGHT.getOrDefault(hl, "无");
                boolean isLiquid = Boolean.TRUE.equals(food.get("is_liquid"));
                String liquid = isLiquid ? " [液体]" : "";

                System.out.printf("  %s%s  %s%n", name, liquid, light);
                System.out.printf("    热量: %skcal  蛋白质: %sg  脂肪: %sg  碳水: %sg%n",
                        food.getOrDefault("calories", "?"),
                        food.getOrDefault("protein", "?"),
                        food.getOrDefault("fat", "?"),
                        food.getOrDefault("carbohydrate", "?"));
                String imgUrl = (String) food.get("image_url");
                if (imgUrl != null && !imgUrl.isEmpty()) {
                    System.out.printf("    图片: %s%n", imgUrl);
                }
                List<Map<String, Object>> units = (List<Map<String, Object>>) food.get("units");
                if (units != null && !units.isEmpty()) {
                    List<String> unitStrs = new ArrayList<>();
                    for (int i = 0; i < Math.min(3, units.size()); i++) {
                        Map<String, Object> u = units.get(i);
                        unitStrs.add(u.get("unit_name") + "(" + u.get("weight") + "g)");
                    }
                    System.out.printf("    常用单位: %s%n", String.join(", ", unitStrs));
                }
                System.out.println();
            }
        }

        int respPage = data.get("page") instanceof Number ? ((Number) data.get("page")).intValue() : 1;
        int respPerPage = data.get("per_page") instanceof Number ? ((Number) data.get("per_page")).intValue() : 20;
        boolean hasMore = Boolean.TRUE.equals(data.get("has_more"));
        System.out.printf("第 %d 页, 每页 %d 条, 共 %d 条%s%n",
                respPage, respPerPage, foods != null ? foods.size() : 0,
                hasMore ? "  有下一页" : "");
    }
}
