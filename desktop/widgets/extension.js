/* Vixzen Widgets v1 — ONE top-bar button: live temp, popup with
 * forecast line + RSS headlines (no API keys). No extra taskbar, dash
 * untouched. Refreshes every 30 min. All failures show "…" or "offline",
 * never an error dialog.
 */
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import Soup from 'gi://Soup';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const WMO = {0: ['☀', 'Clear'], 1: ['🌤', 'Mainly clear'], 2: ['⛅', 'Partly cloudy'],
    3: ['☁', 'Overcast'], 45: ['🌫', 'Fog'], 48: ['🌫', 'Icy fog'],
    51: ['🌦', 'Drizzle'], 53: ['🌦', 'Drizzle'], 55: ['🌦', 'Drizzle'],
    61: ['🌧', 'Rain'], 63: ['🌧', 'Rain'], 65: ['🌧', 'Heavy rain'],
    71: ['❄', 'Snow'], 73: ['❄', 'Snow'], 75: ['❄', 'Heavy snow'],
    80: ['🌦', 'Showers'], 81: ['🌦', 'Showers'], 82: ['🌦', 'Showers'],
    95: ['⛈', 'Storm'], 96: ['⛈', 'Storm+hail'], 99: ['⛈', 'Storm+hail']};
const FEEDS = [
    ['BBC', 'https://feeds.bbci.co.uk/news/world/rss.xml'],
    ['Al Jazeera', 'https://www.aljazeera.com/xml/rss/all.xml'],
];

function unesc(s) {
    return s.replace(/&amp;/g, '&').replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>').replace(/&quot;/g, '"')
        .replace(/&#39;/g, "'").replace(/<!\[CDATA\[/g, '')
        .replace(/\]\]>/g, '').trim();
}

export default class VixzenWidgets extends Extension {
    enable() {
        this._btn = new PanelMenu.Button(0.0, 'Vixzen Widgets', false);
        this._label = new St.Label({ text: '⛅ …', y_align: Clutter.ActorAlign.CENTER });
        this._btn.add_child(this._label);
        Main.panel.addToStatusArea('vixzen-widgets', this._btn, 1, 'right');
        this._btn.menu.connect('open-state-changed', (m, open) => {
            if (open) this._openHeadlines(this._btn.menu);
        });
        this._session = new Soup.Session();
        this._wx = null;
        this._news = [];
        this._refreshWeather();
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1800,
            () => { this._refreshWeather(); return GLib.SOURCE_CONTINUE; });
    }

    disable() {
        if (this._timer) { GLib.source_remove(this._timer); this._timer = 0; }
        this._session?.abort();
        this._session = null;
        this._btn?.destroy();
        this._btn = null;
    }

    _get(url, cb) {
        let msg;
        try {
            msg = Soup.Message.new('GET', url);
        } catch (e) { cb(false, null); return; }
        msg.request_headers.append('User-Agent', 'VixzenOS/0.3');
        this._session.send_and_read_async(msg, GLib.PRIORITY_DEFAULT, null, (s, res) => {
            try {
                const bytes = this._session.send_and_read_finish(res);
                cb(true, new TextDecoder().decode(bytes.get_data()));
            } catch (e) { cb(false, null); }
        });
    }

    _refreshWeather() {
        this._get('http://ip-api.com/json/?fields=lat,lon,city', (ok, body) => {
            if (!ok) return;
            let loc;
            try { loc = JSON.parse(body); } catch (e) { return; }
            if (typeof loc.lat !== 'number') return;
            const url = `https://api.open-meteo.com/v1/forecast?latitude=${loc.lat}` +
                `&longitude=${loc.lon}&current=temperature_2m,weather_code`;
            this._get(url, (ok2, body2) => {
                if (!ok2) return;
                try {
                    const cur = JSON.parse(body2).current;
                    const [icon, text] = WMO[cur.weather_code] ?? ['⛅', ''];
                    this._wx = { temp: Math.round(cur.temperature_2m), icon, text,
                                 city: loc.city ?? '' };
                    this._label.set_text(`${icon} ${this._wx.temp}°`);
                } catch (e) { /* keep "…" */ }
            });
        });
    }

    _openHeadlines(menu) {
        menu.removeAll();
        const w = this._wx;
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem(
            w ? `${w.icon} ${w.temp}°C — ${w.text}${w.city ? ' · ' + w.city : ''}` : 'Weather offline'));
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem('Top stories'));
        const done = items => {
            if (!items.length) {
                const it = new PopupMenu.PopupMenuItem('Offline — no headlines yet');
                it.set_reactive(false);
                menu.addMenuItem(it);
            }
            for (const [src, title, link] of items.slice(0, 6)) {
                const it = new PopupMenu.PopupMenuItem(`${src}: ${title}`);
                it.connect('activate', () => {
                    try { Gio.AppInfo.launch_default_for_uri(link, null); } catch (e) {}
                });
                menu.addMenuItem(it);
            }
        };
        let items = [];
        let pending = FEEDS.length;
        if (!pending) done(items);
        for (const [src, url] of FEEDS) {
            this._get(url, (ok, body) => {
                if (ok && body) {
                    const re = /<item>[\s\S]*?<title>([\s\S]*?)<\/title>[\s\S]*?<link>([\s\S]*?)<\/link>/g;
                    let m;
                    while ((m = re.exec(body)) && items.length < 6) {
                        const t = unesc(m[1]), l = unesc(m[2]);
                        if (t && l.startsWith('http')) items.push([src, t, l]);
                    }
                }
                if (--pending === 0) done(items);
            });
        }
    }
}
