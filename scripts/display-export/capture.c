#include "host.h"
#include <lvgl.h>
#include "custom_status_screen.h"
#ifdef CONFIG_TOTEM_HOST_NAMES
#include <totem/host_names.h>
static struct tn_snapshot name_state;
void totem_host_names_snapshot(struct tn_snapshot *out) { *out = name_state; }
#endif

struct host_state state;
static uint8_t pixels[EXPORT_HEIGHT][EXPORT_WIDTH];
static lv_color_t draw_pixels[EXPORT_WIDTH * EXPORT_HEIGHT];
void widget_dongle_battery_status_inject(const zmk_event_t *event);

static void flush(lv_disp_drv_t *driver, const lv_area_t *area, lv_color_t *colors) {
    for (int y = area->y1; y <= area->y2; ++y)
        for (int x = area->x1; x <= area->x2; ++x) {
            bool lit = colors++->full != 0;
            /* SH1106 MONO10 transport, followed by devicetree inversion-on. */
            if (EXPORT_INVERT) lit = !lit;
            if (x >= 0 && x < EXPORT_WIDTH && y >= 0 && y < EXPORT_HEIGHT)
                pixels[y][x] = lit ? 255 : 0;
        }
    lv_disp_flush_ready(driver);
}

int main(int argc, char **argv) {
    if (argc != 18) return 2;
    state = (struct host_state){
        .transport = atoi(argv[1]), .profile = atoi(argv[2]),
        .connected = atoi(argv[3]), .bonded = atoi(argv[4]), .usb = atoi(argv[5]),
        .battery = atoi(argv[6]), .mods = atoi(argv[9]), .indicators = atoi(argv[10]),
        .wpm = atoi(argv[11]), .layer = argv[12],
    };
#ifdef CONFIG_TOTEM_HOST_NAMES
    name_state.profile = state.profile;
    name_state.mode = atoi(argv[15]);
    name_state.save_failed = atoi(argv[17]);
    tn_display_name(name_state.name, argv[13], argv[14], state.profile);
    snprintf(name_state.draft, sizeof(name_state.draft), "%s", argv[16]);
#endif
    lv_init();
    static lv_disp_draw_buf_t buffer;
    lv_disp_draw_buf_init(&buffer, draw_pixels, NULL, EXPORT_WIDTH * EXPORT_HEIGHT);
    static lv_disp_drv_t driver;
    lv_disp_drv_init(&driver);
    driver.hor_res = EXPORT_WIDTH;
    driver.ver_res = EXPORT_HEIGHT;
    driver.draw_buf = &buffer;
    driver.flush_cb = flush;
    lv_disp_t *display = lv_disp_drv_register(&driver);
#if IS_ENABLED(CONFIG_LV_USE_THEME_MONO)
    lv_theme_t *theme = lv_theme_mono_init(display, IS_ENABLED(CONFIG_ZMK_DISPLAY_INVERT), LV_FONT_DEFAULT);
    theme->font_small = &lv_font_montserrat_12;
    display->theme = theme;
#endif
    lv_scr_load(zmk_display_status_screen());
    for (int side = 0; side < 2; ++side) {
        zmk_event_t event = {side, atoi(argv[7 + side])};
        widget_dongle_battery_status_inject(&event);
    }
    /* Finish the 200 ms selection animations; take a deterministic cat frame. */
    for (int i = 0; i < 30; ++i) {
        lv_tick_inc(10);
        lv_timer_handler();
    }
    lv_refr_now(display);
    printf("P5\n%d %d\n255\n", EXPORT_WIDTH, EXPORT_HEIGHT);
    return fwrite(pixels, 1, sizeof(pixels), stdout) == sizeof(pixels) ? 0 : 1;
}
