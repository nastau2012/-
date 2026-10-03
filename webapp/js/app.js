const tg = window.Telegram?.WebApp;

// ---------------------------------------------------------
// Глобальная диагностика ошибок
// ---------------------------------------------------------

function showFatalError(title, message) {
  console.error("[CalFlow]", title, message);

  const app = document.querySelector("#app");
  if (!app) return;

  const oldError = document.querySelector(".fatal-error");
  if (oldError) oldError.remove();

  const box = document.createElement("div");
  box.className = "card error-card fatal-error";
  box.style.margin = "12px";

  box.innerHTML = `
    <h2>${escapeHtml(title)}</h2>
    <p class="meta" style="margin-top:8px">
      ${escapeHtml(message)}
    </p>
    <button
      type="button"
      class="btn primary block"
      style="margin-top:12px"
      id="fatal-reload-btn"
    >
      Повторить
    </button>
  `;

  app.prepend(box);

  const reloadBtn = box.querySelector("#fatal-reload-btn");
  if (reloadBtn) {
    reloadBtn.addEventListener("click", () => {
      location.reload();
    });
  }
}

window.addEventListener("error", (event) => {
  console.error(
    "[CalFlow] JavaScript error:",
    event.error || event.message
  );

  const message =
    event?.message ||
    event?.error?.message ||
    "Неизвестная ошибка JavaScript";

  showFatalError("Ошибка приложения", message);
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("[CalFlow] Promise error:", event.reason);

  const message =
    event?.reason?.message ||
    String(event?.reason || "Неизвестная ошибка");

  showFatalError("Ошибка загрузки", message);
});


// ---------------------------------------------------------
// Telegram Mini App
// ---------------------------------------------------------

if (tg) {
  try {
    tg.ready();
    tg.expand();

    if (tg.setHeaderColor) {
      tg.setHeaderColor("#0e0f12");
    }

    if (tg.setBackgroundColor) {
      tg.setBackgroundColor("#575151");
    }

    if (tg.setBottomBarColor) {
      tg.setBottomBarColor("#0e0f12");
    }

    console.log("[CalFlow] Telegram WebApp initialized");
    console.log(
      "[CalFlow] initData present:",
      Boolean(tg.initData)
    );
  } catch (e) {
    console.warn(
      "[CalFlow] Telegram WebApp init warning:",
      e
    );
  }
} else {
  console.warn(
    "[CalFlow] Telegram WebApp object is not available"
  );
}


// ---------------------------------------------------------
// Константы и состояние
// ---------------------------------------------------------

const CIRC = 2 * Math.PI * 52;

const state = {
  user: null,
  selectedProduct: null,
  mealType: "lunch",
  searchTimer: null,
  currentView: "home",
  returnToMealAfterProduct: false,
};

const MEAL_TITLE = {
  breakfast: "🌅 Завтрак",
  lunch: "☀️ Обед",
  dinner: "🌙 Ужин",
  snack: "🍎 Перекус",
};


// ---------------------------------------------------------
// Вспомогательные функции
// ---------------------------------------------------------

function $(sel) {
  return document.querySelector(sel);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function toast(msg) {
  const el = $("#toast");

  if (!el) {
    console.warn(
      "[CalFlow] Toast element not found:",
      msg
    );
    return;
  }

  el.textContent = msg;
  el.classList.remove("hidden");

  clearTimeout(toast._t);

  toast._t = setTimeout(() => {
    el.classList.add("hidden");
  }, 2200);
}


// ---------------------------------------------------------
// Локальный API
// GitHub Pages не запускает Python API,
// поэтому данные хранятся в localStorage.
// ---------------------------------------------------------

async function api(path, options = {}) {
  console.log(
    `[CalFlow] Local API: ${
      options.method || "GET"
    } ${path}`
  );

  const STORAGE_KEY = "calflow_data_v1";
  const method = options.method || "GET";

  const body =
    options.body
      ? JSON.parse(options.body)
      : {};

  const DEFAULT_PRODUCTS = [
    {
      id: "p1",
      name: "Овсянка",
      category: "Крупы",
      calories: 366,
      protein: 11.9,
      fat: 7.2,
      carbs: 69.3
    },
    {
      id: "p2",
      name: "Яблоко",
      category: "Фрукты",
      calories: 52,
      protein: 0.3,
      fat: 0.2,
      carbs: 13.8
    },
    {
      id: "p3",
      name: "Банан",
      category: "Фрукты",
      calories: 89,
      protein: 1.1,
      fat: 0.3,
      carbs: 22.8
    },
    {
      id: "p4",
      name: "Куриная грудка",
      category: "Мясо и птица",
      calories: 165,
      protein: 31,
      fat: 3.6,
      carbs: 0
    },
    {
      id: "p5",
      name: "Рис",
      category: "Крупы",
      calories: 344,
      protein: 6.7,
      fat: 0.7,
      carbs: 78.9
    },
    {
      id: "p6",
      name: "Гречка",
      category: "Крупы",
      calories: 313,
      protein: 12.6,
      fat: 3.3,
      carbs: 62.1
    },
    {
      id: "p7",
      name: "Яйцо",
      category: "Яйца",
      calories: 157,
      protein: 12.7,
      fat: 10.9,
      carbs: 0.7
    },
    {
      id: "p8",
      name: "Творог 5%",
      category: "Молочные",
      calories: 121,
      protein: 17.2,
      fat: 5,
      carbs: 1.8
    },
    {
      id: "p9",
      name: "Молоко 2.5%",
      category: "Молочные",
      calories: 52,
      protein: 2.8,
      fat: 2.5,
      carbs: 4.7
    },
    {
      id: "p10",
      name: "Хлеб",
      category: "Хлеб и выпечка",
      calories: 250,
      protein: 7.6,
      fat: 2.8,
      carbs: 49.4
    },
    {
      id: "p11",
      name: "Авокадо",
      category: "Овощи",
      calories: 160,
      protein: 2,
      fat: 14.7,
      carbs: 8.5
    },
    {
      id: "p12",
      name: "Помидор",
      category: "Овощи",
      calories: 18,
      protein: 0.9,
      fat: 0.2,
      carbs: 3.9
    }
  ];

  function loadData() {
    try {
      const raw =
        localStorage.getItem(STORAGE_KEY);

      if (!raw) {
        return {
          user: null,
          meals: [],
          products: []
        };
      }

      const data =
        JSON.parse(raw);

      return {
        user: data.user || null,

        meals:
          Array.isArray(data.meals)
            ? data.meals
            : [],

        products:
          Array.isArray(data.products)
            ? data.products
            : []
      };

    } catch (e) {
      console.error(
        "[CalFlow] localStorage error:",
        e
      );

      return {
        user: null,
        meals: [],
        products: []
      };
    }
  }

  function saveData(data) {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify(data)
    );
  }

  function todayKey() {
    const d = new Date();

    return (
      `${d.getFullYear()}-` +
      `${String(
        d.getMonth() + 1
      ).padStart(2, "0")}-` +
      `${String(
        d.getDate()
      ).padStart(2, "0")}`
    );
  }

  function calculateNorms(
    gender,
    age,
    height,
    weight,
    activity,
    goal
  ) {
    const base =
      gender === "male"
        ? 10 * weight +
          6.25 * height -
          5 * age +
          5
        : 10 * weight +
          6.25 * height -
          5 * age -
          161;

    const factors = {
      sedentary: 1.2,
      light: 1.375,
      moderate: 1.55,
      active: 1.725,
      very_active: 1.9
    };

    let calories =
      base *
      (factors[activity] || 1.55);

    if (goal === "lose") {
      calories -= 300;
    }

    if (goal === "gain") {
      calories += 300;
    }

    calories = Math.max(
      1200,
      Math.round(calories)
    );

    const protein =
      Math.round(weight * 1.6);

    const fat =
      Math.round(weight * 0.8);

    const carbs =
      Math.max(
        0,
        Math.round(
          (
            calories -
            protein * 4 -
            fat * 9
          ) / 4
        )
      );

    return {
      calories,
      protein,
      fat,
      carbs
    };
  }

  function todayMeals(data) {
    return data.meals.filter(
      (m) =>
        m.date === todayKey()
    );
  }

  function totals(meals) {
    return meals.reduce(
      (s, m) => {
        s.calories +=
          Number(m.calories || 0);

        s.protein +=
          Number(m.protein || 0);

        s.fat +=
          Number(m.fat || 0);

        s.carbs +=
          Number(m.carbs || 0);

        return s;
      },
      {
        calories: 0,
        protein: 0,
        fat: 0,
        carbs: 0
      }
    );
  }


  // -------------------------------------------------------
  // Пользователь
  // -------------------------------------------------------

  if (
    path === "/api/me" &&
    method === "GET"
  ) {
    const data =
      loadData();

    return data.user
      ? {
          registered: true,
          user: data.user
        }
      : {
          registered: false
        };
  }


  // -------------------------------------------------------
  // Регистрация
  // -------------------------------------------------------

  if (
    path === "/api/register" &&
    method === "POST"
  ) {
    const data =
      loadData();

    const age =
      Number(body.age);

    const height =
      Number(body.height);

    const weight =
      Number(body.weight);

    if (
      age < 10 ||
      age > 100 ||
      height < 100 ||
      height > 250 ||
      weight < 30 ||
      weight > 300
    ) {
      throw new Error(
        "Проверьте введённые данные"
      );
    }

    const n =
      calculateNorms(
        body.gender,
        age,
        height,
        weight,
        body.activity,
        body.goal
      );

    data.user = {
      telegram_id:
        tg?.initDataUnsafe?.user?.id ||
        "local",

      gender:
        body.gender,

      age,
      height,
      weight,

      activity:
        body.activity,

      goal:
        body.goal,

      calories_norm:
        n.calories,

      protein_norm:
        n.protein,

      fat_norm:
        n.fat,

      carbs_norm:
        n.carbs
    };

    saveData(data);

    return {
      ok: true,
      user: data.user
    };
  }


  // -------------------------------------------------------
  // Главный экран
  // -------------------------------------------------------

  if (
    path === "/api/home" &&
    method === "GET"
  ) {
    const data =
      loadData();

    if (!data.user) {
      return {
        registered: false
      };
    }

    const meals =
      todayMeals(data);

    const t =
      totals(meals);

    const norm =
      Number(
        data.user.calories_norm || 0
      );

    return {
      registered: true,

      user:
        data.user,

      totals:
        t,

      percent:
        norm
          ? Math.round(
              t.calories /
              norm *
              100
            )
          : 0,

      remaining:
        Math.max(
          0,
          Math.round(
            norm -
            t.calories
          )
        ),

      date_label:
        `Сегодня, ${
          new Date().toLocaleDateString(
            "ru-RU",
            {
              weekday: "long"
            }
          )
        }`,

      recent:
        meals
          .slice(-5)
          .reverse()
    };
  }


  // -------------------------------------------------------
  // Дневник — получение
  // -------------------------------------------------------

  if (
    path === "/api/meals" &&
    method === "GET"
  ) {
    const data =
      loadData();

    const meals =
      todayMeals(data);

    return {
      date:
        todayKey(),

      meals,

      totals:
        totals(meals)
    };
  }


  // -------------------------------------------------------
  // Добавление приёма пищи
  // -------------------------------------------------------

  if (
    path === "/api/meals" &&
    method === "POST"
  ) {
    const data =
      loadData();

    const weight =
      Number(
        body.weight_g || 0
      );

    if (
      !body.name &&
      !body.product_id
    ) {
      throw new Error(
        "Не выбран продукт"
      );
    }

    if (
      !weight ||
      weight < 1 ||
      weight > 5000
    ) {
      throw new Error(
        "Вес должен быть от 1 до 5000 г"
      );
    }

    let product = null;

    if (body.product_id) {
      product =
        [
          ...DEFAULT_PRODUCTS,
          ...data.products
        ].find(
          (p) =>
            String(p.id) ===
            String(body.product_id)
        );
    }

    if (!product) {
      product = {
        name:
          body.name,

        calories:
          Number(
            body.calories || 0
          ),

        protein:
          Number(
            body.protein || 0
          ),

        fat:
          Number(
            body.fat || 0
          ),

        carbs:
          Number(
            body.carbs || 0
          )
      };
    }

    const factor =
      weight / 100;

    const mealType =
      body.meal_type ||
      "lunch";

    const meal = {
      id:
        `${Date.now()}-${Math.random()
          .toString(16)
          .slice(2)}`,

      date:
        todayKey(),

      product_name:
        product.name,

      weight_g:
        weight,

      meal_type:
        mealType,

      meal_label:
        MEAL_TITLE[mealType] ||
        mealType,

      calories:
        Number(
          product.calories || 0
        ) * factor,

      protein:
        Number(
          product.protein || 0
        ) * factor,

      fat:
        Number(
          product.fat || 0
        ) * factor,

      carbs:
        Number(
          product.carbs || 0
        ) * factor
    };

    data.meals.push(meal);

    saveData(data);

    return {
      ok: true,
      meal
    };
  }


  // -------------------------------------------------------
  // Удаление приёма пищи
  // -------------------------------------------------------

  if (
    path.startsWith(
      "/api/meals/"
    ) &&
    method === "DELETE"
  ) {
    const data =
      loadData();

    const id =
      path.split("/").pop();

    const before =
      data.meals.length;

    data.meals =
      data.meals.filter(
        (m) =>
          String(m.id) !==
          String(id)
      );

    saveData(data);

    return {
      ok:
        data.meals.length <
        before
    };
  }


  // -------------------------------------------------------
  // Редактирование приёма пищи
  // -------------------------------------------------------

  if (
    path.startsWith(
      "/api/meals/"
    ) &&
    method === "PATCH"
  ) {
    const data =
      loadData();

    const id =
      path.split("/").pop();

    const meal =
      data.meals.find(
        (m) =>
          String(m.id) ===
          String(id)
      );

    if (!meal) {
      throw new Error(
        "Запись не найдена"
      );
    }

    if (body.meal_type) {
      meal.meal_type =
        body.meal_type;

      meal.meal_label =
        MEAL_TITLE[
          body.meal_type
        ] ||
        body.meal_type;
    }

    saveData(data);

    return {
      ok: true,
      meal
    };
  }


  // -------------------------------------------------------
  // Поиск продуктов
  // -------------------------------------------------------

  if (
    path.startsWith(
      "/api/products/search"
    ) &&
    method === "GET"
  ) {
    const data =
      loadData();

    const url =
      new URL(
        path,
        window.location.origin
      );

    const q =
      (
        url.searchParams.get("q") ||
        ""
      )
        .trim()
        .toLowerCase();

    if (q.length < 2) {
      return {
        local: [],
        off: []
      };
    }

    const local =
      [
        ...DEFAULT_PRODUCTS,
        ...data.products
      ].filter(
        (p) =>
          p.name
            .toLowerCase()
            .includes(q)
      );

    if (local.length) {
      return {
        local,
        off: []
      };
    }

    try {
      const offUrl =
        `https://world.openfoodfacts.org/cgi/search.pl` +
        `?search_terms=${encodeURIComponent(q)}` +
        `&search_lang=ru` +
        `&fields=product_name,nutriments` +
        `&json=1` +
        `&page_size=8`;

      const response =
        await fetch(offUrl);

      if (!response.ok) {
        return {
          local: [],
          off: []
        };
      }

      const result =
        await response.json();

      const off =
        (result.products || [])
          .filter(
            (p) =>
              p.product_name
          )
          .map((p) => {
            const n =
              p.nutriments ||
              {};

            return {
              source:
                "off",

              name:
                p.product_name,

              category:
                "Open Food Facts",

              calories:
                Number(
                  n[
                    "energy-kcal_100g"
                  ] || 0
                ),

              protein:
                Number(
                  n.proteins_100g ||
                  0
                ),

              fat:
                Number(
                  n.fat_100g ||
                  0
                ),

              carbs:
                Number(
                  n.carbohydrates_100g ||
                  0
                )
            };
          })
          .filter(
            (p) =>
              p.calories > 0
          );

      return {
        local: [],
        off
      };

    } catch (e) {
      console.error(
        "[CalFlow] Open Food Facts search:",
        e
      );

      return {
        local: [],
        off: []
      };
    }
  }


  // -------------------------------------------------------
  // Добавление своего продукта
  // -------------------------------------------------------

  if (
    path === "/api/products" &&
    method === "POST"
  ) {
    const data =
      loadData();

    const product = {
      id:
        `custom-${Date.now()}`,

      name:
        String(
          body.name || ""
        ).trim(),

      category:
        body.category ||
        "Другое",

      calories:
        Number(
          body.calories || 0
        ),

      protein:
        Number(
          body.protein || 0
        ),

      fat:
        Number(
          body.fat || 0
        ),

      carbs:
        Number(
          body.carbs || 0
        )
    };

    if (
      product.name.length < 2
    ) {
      throw new Error(
        "Укажите название продукта"
      );
    }

    data.products.push(
      product
    );

    saveData(data);

    return {
      ok: true,
      id: product.id
    };
  }


  // -------------------------------------------------------
  // Статистика
  // -------------------------------------------------------

  if (
    path.startsWith(
      "/api/stats"
    ) &&
    method === "GET"
  ) {
    const data =
      loadData();

    if (!data.user) {
      return {
        totals: {
          calories: 0,
          protein: 0,
          fat: 0,
          carbs: 0
        },

        norms: {
          calories: 0,
          protein: 0,
          fat: 0,
          carbs: 0
        },

        days: []
      };
    }

    const url =
      new URL(
        path,
        window.location.origin
      );

    const period =
      url.searchParams.get(
        "period"
      ) ||
      "today";

    const t =
      totals(
        todayMeals(data)
      );

    const n = {
      calories:
        data.user.calories_norm,

      protein:
        data.user.protein_norm,

      fat:
        data.user.fat_norm,

      carbs:
        data.user.carbs_norm
    };

    if (
      period === "today"
    ) {
      return {
        totals: t,
        norms: n,
        days: []
      };
    }

    const count =
      period === "week"
        ? 7
        : 30;

    const days = [];

    for (
      let i = 0;
      i < count;
      i++
    ) {
      const d =
        new Date();

      d.setDate(
        d.getDate() - i
      );

      const key =
        `${d.getFullYear()}-` +
        `${String(
          d.getMonth() + 1
        ).padStart(2, "0")}-` +
        `${String(
          d.getDate()
        ).padStart(2, "0")}`;

      const calories =
        data.meals
          .filter(
            (m) =>
              m.date === key
          )
          .reduce(
            (sum, m) =>
              sum +
              Number(
                m.calories || 0
              ),
            0
          );

      days.push({
        day:
          d.toLocaleDateString(
            "ru-RU",
            {
              day: "2-digit",
              month: "2-digit"
            }
          ),

        calories
      });
    }

    return {
      totals: t,
      norms: n,
      days
    };
  }


  // -------------------------------------------------------
  // Рекомендации
  // -------------------------------------------------------

  if (
    path ===
      "/api/recommendations" &&
    method === "GET"
  ) {
    const data =
      loadData();

    if (!data.user) {
      return {
        tips: []
      };
    }

    const t =
      totals(
        todayMeals(data)
      );

    const tips = [];

    if (
      t.calories === 0
    ) {
      tips.push(
        "Добавьте первый приём пищи, чтобы начать вести дневник."
      );

    } else if (
      t.calories >
      data.user.calories_norm
    ) {
      tips.push(
        "Сегодня потребление калорий выше рассчитанной нормы."
      );

    } else {
      tips.push(
        "Продолжайте фиксировать приёмы пищи в дневнике."
      );
    }

    if (
      t.protein <
      data.user.protein_norm * 0.7
    ) {
      tips.push(
        "Белка пока заметно меньше рассчитанной дневной нормы."
      );
    }

    if (
      t.calories >=
      data.user.calories_norm * 0.8
    ) {
      tips.push(
        "До конца дня учитывайте оставшуюся калорийность рациона."
      );
    }

    return {
      tips
    };
  }


  // -------------------------------------------------------
  // Изменение веса
  // -------------------------------------------------------

  if (
    path === "/api/weight" &&
    method === "POST"
  ) {
    const data =
      loadData();

    if (!data.user) {
      throw new Error(
        "Профиль пользователя не найден"
      );
    }

    const weight =
      Number(body.weight);

    if (
      !weight ||
      weight < 30 ||
      weight > 300
    ) {
      throw new Error(
        "Укажите корректный вес"
      );
    }

    data.user.weight =
      weight;

    const n =
      calculateNorms(
        data.user.gender,
        data.user.age,
        data.user.height,
        weight,
        data.user.activity,
        data.user.goal
      );

    data.user.calories_norm =
      n.calories;

    data.user.protein_norm =
      n.protein;

    data.user.fat_norm =
      n.fat;

    data.user.carbs_norm =
      n.carbs;

    saveData(data);

    return {
      ok: true,
      user: data.user
    };
  }


  throw new Error(
    `Неизвестный локальный API-запрос: ${path}`
  );
}


// ---------------------------------------------------------
// Навигация
// ---------------------------------------------------------

function showView(name) {
  console.log(
    "[CalFlow] showView:",
    name
  );

  document
    .querySelectorAll(".view")
    .forEach(
      (v) =>
        v.classList.add("hidden")
    );

  const el =
    $(`#view-${name}`);

  if (!el) {
    throw new Error(
      `Не найден экран #view-${name}`
    );
  }

  el.classList.remove(
    "hidden"
  );

  state.currentView =
    name;

  const nav =
    $("#main-nav");

  if (!nav) {
    console.warn(
      "[CalFlow] #main-nav not found"
    );
    return;
  }

  if (
    name === "register" ||
    name === "add"
  ) {
    nav.classList.add(
      "hidden"
    );
  } else {
    nav.classList.remove(
      "hidden"
    );

    nav
      .querySelectorAll(
        "button"
      )
      .forEach(
        (b) => {
          const isActive =
            b.dataset.view ===
              name ||
            (
              name === "home" &&
              b.dataset.view ===
                "home"
            );

          b.classList.toggle(
            "active",
            isActive
          );
        }
      );
  }
}


// ---------------------------------------------------------
// Расчёты
// ---------------------------------------------------------

function pct(cur, norm) {
  if (!norm) {
    return 0;
  }

  return Math.round(
    Math.min(
      999,
      (
        Number(cur || 0) /
        Number(norm)
      ) * 100
    )
  );
}

function setRing(percent) {
  const ring =
    $("#cal-ring");

  if (!ring) {
    console.warn(
      "[CalFlow] #cal-ring not found"
    );
    return;
  }

  const p =
    Math.max(
      0,
      Math.min(
        100,
        Number(percent) || 0
      )
    );

  ring.style.strokeDasharray =
    String(CIRC);

  ring.style.strokeDashoffset =
    String(
      CIRC *
      (1 - p / 100)
    );
}


// ---------------------------------------------------------
// Главная
// ---------------------------------------------------------

function renderHome(data) {
  console.log(
    "[CalFlow] renderHome:",
    data
  );

  if (
    !data ||
    !data.user ||
    !data.totals
  ) {
    throw new Error(
      "Сервер вернул неполные данные главной страницы."
    );
  }

  const u =
    data.user;

  const t =
    data.totals;

  const calPct =
    Number(
      data.percent || 0
    );

  const dateLabel =
    $("#date-label");

  const calPctEl =
    $("#cal-pct");

  const calFrac =
    $("#cal-frac");

  const calRemain =
    $("#cal-remain");

  if (
    !dateLabel ||
    !calPctEl ||
    !calFrac ||
    !calRemain
  ) {
    throw new Error(
      "Не найдены элементы главной страницы."
    );
  }

  dateLabel.textContent =
    data.date_label ||
    "Сегодня";

  calPctEl.textContent =
    `${calPct}%`;

  calFrac.textContent =
    `${Math.round(
      Number(
        t.calories || 0
      )
    )} / ` +
    `${Math.round(
      Number(
        u.calories_norm || 0
      )
    )} ккал ✅`;

  calRemain.textContent =
    `Осталось: ${
      Number(
        data.remaining || 0
      )
    } ккал`;

  setRing(
    calPct
  );

  const macros = [
    [
      "p",
      t.protein,
      u.protein_norm
    ],
    [
      "f",
      t.fat,
      u.fat_norm
    ],
    [
      "c",
      t.carbs,
      u.carbs_norm
    ]
  ];

  macros.forEach(
    ([key, cur, norm]) => {
      const p =
        pct(
          cur,
          norm
        );

      const pctEl =
        $(`#${key}-pct`);

      const valEl =
        $(`#${key}-val`);

      const barEl =
        $(`#${key}-bar`);

      if (pctEl) {
        pctEl.textContent =
          `${p}%`;
      }

      if (valEl) {
        valEl.textContent =
          `${Math.round(
            Number(cur || 0)
          )} / ` +
          `${Math.round(
            Number(norm || 0)
          )}г`;
      }

      if (barEl) {
        barEl.style.width =
          `${Math.min(
            100,
            p
          )}%`;
      }
    }
  );

  const list =
    $("#recent-list");

  if (!list) {
    throw new Error(
      "Не найден список последних приёмов пищи."
    );
  }

  list.innerHTML = "";

  if (
    !Array.isArray(
      data.recent
    ) ||
    !data.recent.length
  ) {
    list.innerHTML = `
      <li>
        <div>
          <div>Пока пусто</div>
          <div class="meta">
            Добавьте первый приём пищи
          </div>
        </div>
      </li>
    `;

    return;
  }

  data.recent.forEach(
    (m) => {
      const li =
        document.createElement(
          "li"
        );

      li.innerHTML = `
        <div>
          <div>
            ${escapeHtml(
              m.meal_label || ""
            )}:
            ${escapeHtml(
              m.product_name || ""
            )}
          </div>

          <div class="meta">
            ${escapeHtml(
              m.weight_g ?? 0
            )} г
          </div>
        </div>

        <div class="kcal">
          ${Math.round(
            Number(
              m.calories || 0
            )
          )} ккал
        </div>
      `;

      list.appendChild(li);
    }
  );
}

async function loadHome() {
  console.log(
    "[CalFlow] loading /api/home"
  );

  const data =
    await api(
      "/api/home"
    );

  console.log(
    "[CalFlow] /api/home data:",
    data
  );

  if (
    !data.registered
  ) {
    showView(
      "register"
    );

    return false;
  }

  state.user =
    data.user;

  renderHome(
    data
  );

  return true;
}


// ---------------------------------------------------------
// Дневник
// ---------------------------------------------------------

async function loadDiary() {
  const data =
    await api(
      "/api/meals"
    );

  const list =
    $("#diary-list");

  if (!list) {
    throw new Error(
      "Не найден список дневника."
    );
  }

  list.innerHTML = "";

  if (
    !Array.isArray(
      data.meals
    ) ||
    !data.meals.length
  ) {
    list.innerHTML = `
      <li>
        <div>Записей нет</div>
      </li>
    `;

    return;
  }

  data.meals.forEach(
    (m) => {
      const li =
        document.createElement(
          "li"
        );

      li.innerHTML = `
        <div>
          <div>
            ${escapeHtml(
              m.meal_label || ""
            )}:
            ${escapeHtml(
              m.product_name || ""
            )}
          </div>

          <div class="meta">
            ${escapeHtml(
              m.weight_g ?? 0
            )} г ·
            Б ${escapeHtml(
              m.protein ?? 0
            )}
            Ж ${escapeHtml(
              m.fat ?? 0
            )}
            У ${escapeHtml(
              m.carbs ?? 0
            )}
          </div>
        </div>

        <div>
          <div class="kcal">
            ${Math.round(
              Number(
                m.calories || 0
              )
            )} ккал
          </div>

          <div class="actions">
            <button
              type="button"
              class="mini"
              data-del="${escapeHtml(
                m.id
              )}"
            >
              Удалить
            </button>
          </div>
        </div>
      `;

      list.appendChild(li);
    }
  );

  list
    .querySelectorAll(
      "[data-del]"
    )
    .forEach(
      (btn) => {
        btn.addEventListener(
          "click",
          async () => {
            try {
              await api(
                `/api/meals/${btn.dataset.del}`,
                {
                  method:
                    "DELETE"
                }
              );

              toast(
                "Удалено"
              );

              await loadDiary();
              await loadHome();

            } catch (e) {
              toast(
                e.message ||
                "Не удалось удалить"
              );
            }
          }
        );
      }
    );
}


// ---------------------------------------------------------
// Добавление приёма пищи
// ---------------------------------------------------------

function openAddMeal() {
  state.selectedProduct =
    null;

  const name =
    $("#add-name");

  const query =
    $("#product-query");

  const results =
    $("#search-results");

  const weight =
    $("#add-weight");

  if (name) {
    name.value = "";
  }

  if (query) {
    query.value = "";
  }

  if (results) {
    results.innerHTML = "";
  }

  if (weight) {
    weight.value = "100";
  }

  updateAddTotal();

  setMealType(
    state.mealType ||
    "lunch"
  );

  showView(
    "add"
  );
}

function setMealType(type) {
  state.mealType =
    type;

  const title =
    $("#add-meal-title");

  if (title) {
    title.textContent =
      MEAL_TITLE[type] ||
      type;
  }

  document
    .querySelectorAll(
      "#meal-tabs button"
    )
    .forEach(
      (b) => {
        b.classList.toggle(
          "active",
          b.dataset.meal ===
            type
        );
      }
    );
}

function updateAddTotal() {
  const weightEl =
    $("#add-weight");

  if (!weightEl) {
    return;
  }

  const w =
    parseFloat(
      weightEl.value
    ) || 0;

  const p =
    state.selectedProduct;

  const total =
    $("#add-total");

  if (!total) {
    return;
  }

  if (!p) {
    total.textContent =
      "🔥 Всего: 0 ккал";

    return;
  }

  const cal =
    Math.round(
      (
        Number(
          p.calories || 0
        ) *
        w
      ) / 100
    );

  total.textContent =
    `🔥 Всего: ${cal} ккал`;
}


// ---------------------------------------------------------
// Поиск продуктов
// ---------------------------------------------------------

function renderSearchResults(
  container,
  local,
  off,
  onPick
) {
  if (!container) {
    return;
  }

  container.innerHTML =
    "";

  const localItems =
    Array.isArray(local)
      ? local
      : [];

  const offItems =
    Array.isArray(off)
      ? off
      : [];

  const items = [
    ...localItems.map(
      (x) => ({
        ...x,
        _badge: "local"
      })
    ),

    ...offItems.map(
      (x) => ({
        ...x,
        _badge: "off"
      })
    )
  ];

  if (!items.length) {
    container.innerHTML = `
      <div
        class="meta"
        style="padding:8px;color:var(--muted)"
      >
        Ничего не найдено
      </div>
    `;

    return;
  }

  items.forEach(
    (item) => {
      const btn =
        document.createElement(
          "button"
        );

      btn.type =
        "button";

      btn.className =
        "search-item";

      let badge =
        "";

      if (
        item._badge ===
        "off"
      ) {
        badge =
          `<span class="badge off">OFF</span>`;

      } else if (
        item.owner_id
      ) {
        badge =
          `<span class="badge">мой продукт</span>`;

      } else {
        badge =
          `<span class="badge">база</span>`;
      }

      btn.innerHTML = `
        <strong>
          ${escapeHtml(
            item.name || ""
          )}
        </strong>

        ${badge}

        <small>
          ${Math.round(
            Number(
              item.calories || 0
            )
          )}
          ккал / 100 г ·
          Б ${Number(
            item.protein || 0
          )}
          Ж ${Number(
            item.fat || 0
          )}
          У ${Number(
            item.carbs || 0
          )}
        </small>
      `;

      btn.addEventListener(
        "click",
        () => onPick(item)
      );

      container.appendChild(
        btn
      );
    }
  );
}

async function searchProducts(
  q,
  container,
  onPick
) {
  if (!container) {
    return;
  }

  if (
    q.trim().length < 2
  ) {
    container.innerHTML =
      "";

    return;
  }

  container.innerHTML =
    `<div class="meta" style="padding:8px">Поиск…</div>`;

  try {
    const data =
      await api(
        `/api/products/search?q=${encodeURIComponent(
          q
        )}`
      );

    renderSearchResults(
      container,
      data.local || [],
      data.off || [],
      onPick
    );

  } catch (e) {
    console.error(
      "[CalFlow] Product search error:",
      e
    );

    container.innerHTML = `
      <div
        class="meta"
        style="padding:8px"
      >
        Ошибка поиска
      </div>
    `;
  }
}

function pickProduct(item) {
  state.selectedProduct =
    item;

  const name =
    $("#add-name");

  if (name) {
    name.value =
      item.name || "";
  }

  updateAddTotal();

  const results =
    $("#search-results");

  if (results) {
    results.innerHTML =
      "";
  }

  toast(
    "Продукт выбран"
  );
}


// ---------------------------------------------------------
// Сохранение приёма пищи
// ---------------------------------------------------------

async function confirmAdd() {
  const p =
    state.selectedProduct;

  const weightEl =
    $("#add-weight");

  const weight =
    parseFloat(
      weightEl?.value
    ) || 0;

  if (!p) {
    toast(
      "Выберите продукт"
    );

    return;
  }

  if (
    !weight ||
    weight < 1
  ) {
    toast(
      "Укажите вес"
    );

    return;
  }

  const body = {
    meal_type:
      state.mealType,

    weight_g:
      weight
  };

  if (
    p.source === "local" &&
    p.id
  ) {
    body.product_id =
      p.id;

  } else {
    body.name =
      p.name;

    body.calories =
      p.calories;

    body.protein =
      p.protein;

    body.fat =
      p.fat;

    body.carbs =
      p.carbs;

    body.category =
      p.category ||
      "Open Food Facts";

    if (p.off_id) {
      body.off_id =
        p.off_id;
    }
  }

  await api(
    "/api/meals",
    {
      method: "POST",

      body:
        JSON.stringify(
          body
        )
    }
  );

  toast(
    "Добавлено в дневник"
  );

  showView(
    "home"
  );

  await loadHome();
}


// ---------------------------------------------------------
// Свой продукт
// ---------------------------------------------------------

function openCustomProductForm(
  prefillName = "",
  returnToMeal = false
) {
  state.returnToMealAfterProduct =
    returnToMeal;

  const form =
    $("#custom-product-form");

  if (form) {
    form.classList.remove(
      "hidden"
    );
  }

  const name =
    $("#custom-name");

  const category =
    $("#custom-category");

  const calories =
    $("#custom-calories");

  const protein =
    $("#custom-protein");

  const fat =
    $("#custom-fat");

  const carbs =
    $("#custom-carbs");

  if (name) {
    name.value =
      prefillName;
  }

  if (category) {
    category.value =
      "Другое";
  }

  if (calories) {
    calories.value =
      "";
  }

  if (protein) {
    protein.value =
      "";
  }

  if (fat) {
    fat.value =
      "";
  }

  if (carbs) {
    carbs.value =
      "";
  }

  showView(
    "products"
  );

  setTimeout(
    () => {
      if (name) {
        name.focus();
      }
    },
    50
  );
}

function closeCustomProductForm() {
  const form =
    $("#custom-product-form");

  if (form) {
    form.classList.add(
      "hidden"
    );
  }

  state.returnToMealAfterProduct =
    false;
}

async function saveCustomProduct(
  event
) {
  event.preventDefault();

  const body = {
    name:
      $("#custom-name")
        ?.value
        .trim() ||
      "",

    category:
      $("#custom-category")
        ?.value ||
      "Другое",

    calories:
      Number(
        $("#custom-calories")
          ?.value
      ),

    protein:
      Number(
        $("#custom-protein")
          ?.value
      ),

    fat:
      Number(
        $("#custom-fat")
          ?.value
      ),

    carbs:
      Number(
        $("#custom-carbs")
          ?.value
      )
  };

  if (
    body.name.length < 2
  ) {
    toast(
      "Укажите название продукта"
    );

    return;
  }

  if (
    [
      body.calories,
      body.protein,
      body.fat,
      body.carbs
    ].some(
      (value) =>
        !Number.isFinite(
          value
        )
    )
  ) {
    toast(
      "Заполните КБЖУ"
    );

    return;
  }

  if (
    body.calories < 0 ||
    body.calories > 5000 ||
    body.protein < 0 ||
    body.protein > 100 ||
    body.fat < 0 ||
    body.fat > 100 ||
    body.carbs < 0 ||
    body.carbs > 100
  ) {
    toast(
      "Проверьте значения КБЖУ"
    );

    return;
  }

  try {
    const result =
      await api(
        "/api/products",
        {
          method:
            "POST",

          body:
            JSON.stringify(
              body
            )
        }
      );

    toast(
      "Продукт сохранён"
    );

    const product = {
      source:
        "local",

      id:
        result.id,

      name:
        body.name,

      category:
        body.category,

      calories:
        body.calories,

      protein:
        body.protein,

      fat:
        body.fat,

      carbs:
        body.carbs
    };

    const returnToMeal =
      state.returnToMealAfterProduct;

    closeCustomProductForm();

    if (returnToMeal) {
      state.returnToMealAfterProduct =
        false;

      openAddMeal();

      pickProduct(
        product
      );

    } else {
      const query =
        $("#prod-query");

      if (query) {
        query.value =
          body.name;
      }

      renderSearchResults(
        $("#prod-results"),
        [product],
        [],
        (item) => {
          state.selectedProduct =
            item;

          openAddMeal();

          pickProduct(
            item
          );
        }
      );
    }

  } catch (e) {
    console.error(
      "[CalFlow] Save product error:",
      e
    );

    toast(
      e.message ||
      "Не удалось сохранить продукт"
    );
  }
}


// ---------------------------------------------------------
// Статистика
// ---------------------------------------------------------

async function loadStats(
  period = "today"
) {
  const [
    stats,
    tips
  ] =
    await Promise.all([
      api(
        `/api/stats?period=${period}`
      ),

      api(
        "/api/recommendations"
      )
    ]);

  const body =
    $("#stats-body");

  if (!body) {
    throw new Error(
      "Не найден блок статистики."
    );
  }

  if (
    period === "today"
  ) {
    const t =
      stats.totals;

    const n =
      stats.norms;

    body.innerHTML = `
      <div class="stat-row">
        <span>Калории</span>
        <strong>
          ${Math.round(
            Number(
              t.calories || 0
            )
          )}
          /
          ${Math.round(
            Number(
              n.calories || 0
            )
          )}
        </strong>
      </div>

      <div class="stat-row">
        <span>Белки</span>
        <strong>
          ${Math.round(
            Number(
              t.protein || 0
            )
          )}
          /
          ${Math.round(
            Number(
              n.protein || 0
            )
          )} г
        </strong>
      </div>

      <div class="stat-row">
        <span>Жиры</span>
        <strong>
          ${Math.round(
            Number(
              t.fat || 0
            )
          )}
          /
          ${Math.round(
            Number(
              n.fat || 0
            )
          )} г
        </strong>
      </div>

      <div class="stat-row">
        <span>Углеводы</span>
        <strong>
          ${Math.round(
            Number(
              t.carbs || 0
            )
          )}
          /
          ${Math.round(
            Number(
              n.carbs || 0
            )
          )} г
        </strong>
      </div>
    `;

  } else {
    if (
      !Array.isArray(
        stats.days
      ) ||
      !stats.days.length
    ) {
      body.innerHTML =
        `<p class="meta">Недостаточно данных</p>`;

    } else {
      body.innerHTML =
        stats.days
          .map(
            (d) => `
              <div class="stat-row">
                <span>
                  ${escapeHtml(
                    d.day || ""
                  )}
                </span>

                <strong>
                  ${Math.round(
                    Number(
                      d.calories || 0
                    )
                  )} ккал
                </strong>
              </div>
            `
          )
          .join("");
    }
  }

  const tipsList =
    $("#tips-list");

  if (tipsList) {
    tipsList.innerHTML =
      (tips.tips || [])
        .map(
          (t) =>
            `<li>${escapeHtml(
              t
            )}</li>`
        )
        .join("");
  }
}


// ---------------------------------------------------------
// Профиль
// ---------------------------------------------------------

async function loadProfile() {
  const data =
    await api(
      "/api/me"
    );

  if (!data.user) {
    throw new Error(
      "Профиль пользователя не найден."
    );
  }

  const u =
    data.user;

  state.user =
    u;

  const goalMap = {
    lose:
      "Похудение",

    maintain:
      "Поддержание веса",

    gain:
      "Набор массы"
  };

  const actMap = {
    sedentary:
      "Малоподвижный",

    light:
      "Лёгкая",

    moderate:
      "Средняя",

    active:
      "Высокая",

    very_active:
      "Очень высокая"
  };

  const card =
    $("#profile-card");

  if (!card) {
    throw new Error(
      "Не найден блок профиля."
    );
  }

  card.innerHTML = `
    <div class="profile-grid">

      <div>
        <span>Пол</span>
        <strong>
          ${
            u.gender === "male"
              ? "Мужской"
              : "Женский"
          }
        </strong>
      </div>

      <div>
        <span>Возраст</span>
        <strong>
          ${escapeHtml(
            u.age
          )}
        </strong>
      </div>

      <div>
        <span>Рост</span>
        <strong>
          ${escapeHtml(
            u.height
          )} см
        </strong>
      </div>

      <div>
        <span>Вес</span>
        <strong>
          ${escapeHtml(
            u.weight
          )} кг
        </strong>
      </div>

      <div>
        <span>Активность</span>
        <strong>
          ${escapeHtml(
            actMap[
              u.activity
            ] ||
            u.activity ||
            ""
          )}
        </strong>
      </div>

      <div>
        <span>Цель</span>
        <strong>
          ${escapeHtml(
            goalMap[
              u.goal
            ] ||
            u.goal ||
            ""
          )}
        </strong>
      </div>

    </div>

    <div style="margin-top:14px">

      <div class="stat-row">
        <span>Норма калорий</span>

        <strong>
          ${Math.round(
            Number(
              u.calories_norm ||
              0
            )
          )} ккал
        </strong>
      </div>

      <div class="stat-row">
        <span>
          Белки / Жиры / Углеводы
        </span>

        <strong>
          ${escapeHtml(
            u.protein_norm ??
            0
          )}
          /
          ${escapeHtml(
            u.fat_norm ??
            0
          )}
          /
          ${escapeHtml(
            u.carbs_norm ??
            0
          )}
          г
        </strong>
      </div>

    </div>
  `;
}


// ---------------------------------------------------------
// Привязка интерфейса
// ---------------------------------------------------------

function bindUI() {
  console.log(
    "[CalFlow] Binding UI"
  );

  const mainNav =
    $("#main-nav");

  if (!mainNav) {
    throw new Error(
      "Не найдено главное меню #main-nav."
    );
  }

  mainNav.addEventListener(
    "click",
    async (e) => {
      const btn =
        e.target.closest(
          "button[data-view]"
        );

      if (!btn) {
        return;
      }

      const view =
        btn.dataset.view;

      try {
        if (
          view === "home"
        ) {
          showView("home");
          await loadHome();

        } else if (
          view === "stats"
        ) {
          showView("stats");
          await loadStats(
            "today"
          );

        } else if (
          view === "products"
        ) {
          showView(
            "products"
          );

        } else if (
          view === "profile"
        ) {
          showView(
            "profile"
          );

          await loadProfile();
        }

      } catch (e) {
        console.error(
          "[CalFlow] Navigation error:",
          e
        );

        toast(
          e.message ||
          "Не удалось загрузить раздел"
        );
      }
    }
  );


  // -------------------------------------------------------
  // Добавить приём пищи
  // -------------------------------------------------------

  const btnAddMeal =
    $("#btn-add-meal");

  if (btnAddMeal) {
    btnAddMeal.addEventListener(
      "click",
      openAddMeal
    );
  }


  const btnDiaryAdd =
    $("#btn-diary-add");

  if (btnDiaryAdd) {
    btnDiaryAdd.addEventListener(
      "click",
      openAddMeal
    );
  }


  const btnCancelAdd =
    $("#btn-cancel-add");

  if (btnCancelAdd) {
    btnCancelAdd.addEventListener(
      "click",
      async () => {
        try {
          showView(
            "home"
          );

          await loadHome();

        } catch (e) {
          toast(
            e.message
          );
        }
      }
    );
  }


  const btnConfirmAdd =
    $("#btn-confirm-add");

  if (btnConfirmAdd) {
    btnConfirmAdd.addEventListener(
      "click",
      () => {
        confirmAdd()
          .catch(
            (e) =>
              toast(
                e.message
              )
          );
      }
    );
  }


  const addWeight =
    $("#add-weight");

  if (addWeight) {
    addWeight.addEventListener(
      "input",
      updateAddTotal
    );
  }


  // -------------------------------------------------------
  // Свой продукт из формы приёма пищи
  // -------------------------------------------------------

  const btnAddCustomFromMeal =
    $("#btn-add-custom-from-meal");

  if (
    btnAddCustomFromMeal
  ) {
    btnAddCustomFromMeal.addEventListener(
      "click",
      () => {
        const q =
          $("#product-query")
            ?.value
            .trim() ||
          "";

        openCustomProductForm(
          q,
          true
        );
      }
    );
  }


  // -------------------------------------------------------
  // Свой продукт
  // -------------------------------------------------------

  const btnOpenProductForm =
    $("#btn-open-product-form");

  if (
    btnOpenProductForm
  ) {
    btnOpenProductForm.addEventListener(
      "click",
      () =>
        openCustomProductForm()
    );
  }


  const btnCancelProductForm =
    $("#btn-cancel-product-form");

  if (
    btnCancelProductForm
  ) {
    btnCancelProductForm.addEventListener(
      "click",
      closeCustomProductForm
    );
  }


  const customProductForm =
    $("#custom-product-form");

  if (
    customProductForm
  ) {
    customProductForm.addEventListener(
      "submit",
      saveCustomProduct
    );
  }


  // -------------------------------------------------------
  // Тип приёма пищи
  // -------------------------------------------------------

  const mealTabs =
    $("#meal-tabs");

  if (mealTabs) {
    mealTabs.addEventListener(
      "click",
      (e) => {
        const b =
          e.target.closest(
            "button[data-meal]"
          );

        if (b) {
          setMealType(
            b.dataset.meal
          );
        }
      }
    );
  }


  // -------------------------------------------------------
  // Поиск продуктов при добавлении еды
  // -------------------------------------------------------

  const productQuery =
    $("#product-query");

  if (productQuery) {
    productQuery.addEventListener(
      "input",
      (e) => {
        clearTimeout(
          state.searchTimer
        );

        state.searchTimer =
          setTimeout(
            () => {
              searchProducts(
                e.target.value,
                $("#search-results"),
                pickProduct
              );
            },
            350
          );
      }
    );
  }


  // -------------------------------------------------------
  // Поиск в разделе продуктов
  // -------------------------------------------------------

  const prodQuery =
    $("#prod-query");

  if (prodQuery) {
    prodQuery.addEventListener(
      "input",
      (e) => {
        clearTimeout(
          state.searchTimer
        );

        state.searchTimer =
          setTimeout(
            () => {
              searchProducts(
                e.target.value,
                $("#prod-results"),
                (item) => {
                  state.selectedProduct =
                    item;

                  openAddMeal();

                  pickProduct(
                    item
                  );
                }
              );
            },
            350
          );
      }
    );
  }


  // -------------------------------------------------------
  // Переключение периода статистики
  // -------------------------------------------------------

  document
    .querySelectorAll(
      ".seg button"
    )
    .forEach(
      (b) => {
        b.addEventListener(
          "click",
          async () => {
            try {
              document
                .querySelectorAll(
                  ".seg button"
                )
                .forEach(
                  (x) =>
                    x.classList.remove(
                      "active"
                    )
                );

              b.classList.add(
                "active"
              );

              await loadStats(
                b.dataset.period
              );

            } catch (e) {
              toast(
                e.message ||
                "Ошибка загрузки статистики"
              );
            }
          }
        );
      }
    );


  // -------------------------------------------------------
  // Регистрация
  // -------------------------------------------------------

  const regForm =
    $("#reg-form");

  if (regForm) {
    regForm.addEventListener(
      "submit",
      async (e) => {
        e.preventDefault();

        const fd =
          new FormData(
            e.target
          );

        const body =
          Object.fromEntries(
            fd.entries()
          );

        body.age =
          Number(
            body.age
          );

        body.height =
          Number(
            body.height
          );

        body.weight =
          Number(
            body.weight
          );

        try {
          await api(
            "/api/register",
            {
              method:
                "POST",

              body:
                JSON.stringify(
                  body
                )
            }
          );

          toast(
            "Профиль сохранён"
          );

          showView(
            "home"
          );

          await loadHome();

        } catch (err) {
          toast(
            err.message ||
            "Ошибка регистрации"
          );
        }
      }
    );
  }


  // -------------------------------------------------------
  // Изменение веса
  // -------------------------------------------------------

  const weightForm =
    $("#weight-form");

  if (weightForm) {
    weightForm.addEventListener(
      "submit",
      async (e) => {
        e.preventDefault();

        try {
          const weight =
            Number(
              new FormData(
                e.target
              ).get(
                "weight"
              )
            );

          if (
            !weight ||
            weight < 30
          ) {
            toast(
              "Укажите корректный вес"
            );

            return;
          }

          await api(
            "/api/weight",
            {
              method:
                "POST",

              body:
                JSON.stringify({
                  weight
                })
            }
          );

          toast(
            "Вес сохранён"
          );

          e.target.reset();

          await loadProfile();

        } catch (err) {
          toast(
            err.message ||
            "Не удалось сохранить вес"
          );
        }
      }
    );
  }

  console.log(
    "[CalFlow] UI binding complete"
  );
}


// ---------------------------------------------------------
// Запуск приложения
// ---------------------------------------------------------

async function boot() {
  console.log(
    "[CalFlow] ==================="
  );

  console.log(
    "[CalFlow] boot started"
  );

  console.log(
    "[CalFlow] Telegram:",
    Boolean(tg)
  );

  console.log(
    "[CalFlow] initData:",
    Boolean(
      tg?.initData
    )
  );

  console.log(
    "[CalFlow] ==================="
  );

  try {
    // Сначала привязываем интерфейс.
    bindUI();

    console.log(
      "[CalFlow] UI bound successfully"
    );

    // Получаем информацию о пользователе.
    console.log(
      "[CalFlow] requesting /api/me"
    );

    const me =
      await api(
        "/api/me"
      );

    console.log(
      "[CalFlow] /api/me OK:",
      me
    );

    // Новый пользователь.
    if (
      !me.registered
    ) {
      console.log(
        "[CalFlow] user is not registered"
      );

      showView(
        "register"
      );

      return;
    }

    // Пользователь зарегистрирован.
    state.user =
      me.user;

    console.log(
      "[CalFlow] showing home"
    );

    showView(
      "home"
    );

    console.log(
      "[CalFlow] loading home"
    );

    await loadHome();

    console.log(
      "[CalFlow] home loaded successfully"
    );

  } catch (e) {
    console.error(
      "[CalFlow] BOOT ERROR:",
      e
    );

    const msg =
      String(
        e?.message || e
      );

    const isAuth =
      /auth|authorization|initdata|401/i
        .test(msg);

    showFatalError(
      isAuth
        ? "Не удалось авторизоваться"
        : "Не удалось загрузить приложение",

      isAuth
        ? "Откройте CalFlow именно внутри Telegram."
        : msg
    );
  }
}


// ---------------------------------------------------------
// Запуск
// ---------------------------------------------------------

boot();
