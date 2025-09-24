import os


def create_file(path, content=""):
    # Upewnij się, że katalog istnieje
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def create_directory_structure(base_path, structure):
    for key, value in structure.items():
        path = os.path.join(base_path, key)
        if isinstance(value, dict):
            os.makedirs(path, exist_ok=True)
            create_directory_structure(path, value)
        else:
            create_file(path, value)


def create_structure():
    structure = {
        "project_root": {
            "backend": {
                "src": {
                    "config": {
                        "database.js": """
const { Pool } = require('pg');

const pool = new Pool({
  user: 'your_username',
  host: 'localhost',
  database: 'your_database_name',
  password: 'your_password',
  port: 5432,
});

module.exports = {
  query: (text, params) => pool.query(text, params),
};
"""
                    },
                    "controllers": {
                        "adminController.js": """
const db = require('../config/database');
const emailService = require('../services/emailService');

exports.getFormularzList = async (req, res) => {
  try {
    const result = await db.query('SELECT * FROM formularz ORDER BY data_utworzenia DESC');
    res.json(result.rows);
  } catch (err) {
    res.status(500).json({ error: 'Błąd serwera' });
  }
};

exports.assignFormularz = async (req, res) => {
  const { formularzId, pracownikId } = req.body;
  try {
    await db.query(
      'UPDATE formularz SET pracownik_id = $1, status = $2, data_przypisania = CURRENT_TIMESTAMP WHERE id = $3',
      [pracownikId, 'w_toku', formularzId]
    );
    const pracownik = await db.query('SELECT email FROM uzytkownik WHERE id = $1', [pracownikId]);
    await emailService.sendEmail(
      pracownik.rows[0].email,
      'Nowy formularz do analizy',
      `Przypisano Ci nowy formularz o ID ${formularzId} do analizy.`
    );
    res.json({ message: 'Formularz przypisany pomyślnie' });
  } catch (err) {
    res.status(500).json({ error: 'Błąd serwera' });
  }
};

exports.verifyFormularz = async (req, res) => {
  const { formularzId, status, uwagi } = req.body;
  try {
    await db.query(
      'UPDATE formularz SET status = $1, data_aktualizacji = CURRENT_TIMESTAMP WHERE id = $2',
      [status, formularzId]
    );
    if (status === 'zrealizowany') {
      const klient = await db.query('SELECT email FROM uzytkownik WHERE id = (SELECT uzytkownik_id FROM formularz WHERE id = $1)', [formularzId]);
      await emailService.sendEmail(
        klient.rows[0].email,
        'Certyfikat energetyczny gotowy',
        'Twój certyfikat energetyczny jest gotowy. Możesz go pobrać z naszej strony.'
      );
    } else if (status === 'do_poprawy') {
      const pracownik = await db.query('SELECT email FROM uzytkownik WHERE id = (SELECT pracownik_id FROM formularz WHERE id = $1)', [formularzId]);
      await emailService.sendEmail(
        pracownik.rows[0].email,
        'Formularz wymaga poprawy',
        `Formularz o ID ${formularzId} wymaga poprawy. Uwagi: ${uwagi}`
      );
    }
    res.json({ message: 'Status formularza zaktualizowany' });
  } catch (err) {
    res.status(500).json({ error: 'Błąd serwera' });
  }
};
""",
                        "formController.js": """
const db = require('../config/database');
const emailService = require('../services/emailService');

exports.submitForm = async (req, res) => {
  const { landingPageId, userId, type, formData } = req.body;
  try {
    const result = await db.query(
      'INSERT INTO formularz (landing_page_id, uzytkownik_id, typ, dane_formularza) VALUES ($1, $2, $3, $4) RETURNING id',
      [landingPageId, userId, type, JSON.stringify(formData)]
    );
    const formularzId = result.rows[0].id;
    
    // Wysyłanie powiadomienia do audytorów
    const audytorzy = await db.query('SELECT id, email FROM uzytkownik WHERE typ = $1', ['audytor']);
    for (let audytor of audytorzy.rows) {
      await db.query(
        'INSERT INTO powiadomienie (uzytkownik_id, tresc) VALUES ($1, $2)',
        [audytor.id, `Nowy formularz o ID ${formularzId} oczekuje na przypisanie.`]
      );
      await emailService.sendEmail(
        audytor.email,
        'Nowy formularz do przypisania',
        `Nowy formularz o ID ${formularzId} oczekuje na przypisanie.`
      );
    }
    
    res.json({ message: 'Formularz przesłany pomyślnie', formularzId });
  } catch (err) {
    res.status(500).json({ error: 'Błąd serwera' });
  }
};

exports.getFormStatus = async (req, res) => {
  const { formularzId } = req.params;
  try {
    const result = await db.query('SELECT status FROM formularz WHERE id = $1', [formularzId]);
    if (result.rows.length === 0) {
      res.status(404).json({ error: 'Formularz nie znaleziony' });
    } else {
      res.json({ status: result.rows[0].status });
    }
  } catch (err) {
    res.status(500).json({ error: 'Błąd serwera' });
  }
};
""",
                        "landingPageController.js": """
const db = require('../config/database');

exports.getLandingPageContent = async (req, res) => {
  const { domain } = req.params;
  try {
    const landingPage = await db.query('SELECT * FROM landing_page WHERE domena = $1', [domain]);
    if (landingPage.rows.length === 0) {
      return res.status(404).json({ error: 'Strona nie znaleziona' });
    }
    const landingPageId = landingPage.rows[0].id;
    
    const sections = await db.query('SELECT * FROM sekcja WHERE landing_page_id = $1', [landingPageId]);
    const blogPosts = await db.query('SELECT * FROM post_blog WHERE landing_page_id = $1 ORDER BY data_publikacji DESC LIMIT 3', [landingPageId]);
    
    res.json({
      landingPage: landingPage.rows[0],
      sections: sections.rows,
      blogPosts: blogPosts.rows
    });
  } catch (err) {
    res.status(500).json({ error: 'Błąd serwera' });
  }
};

exports.updateLandingPageContent = async (req, res) => {
  const { landingPageId } = req.params;
  const { sections, blogPosts } = req.body;
  
  try {
    await db.query('BEGIN');
    
    for (let section of sections) {
      await db.query(
        'UPDATE sekcja SET nazwa = $1, tresc = $2, obraz_url = $3, data_aktualizacji = CURRENT_TIMESTAMP WHERE id = $4 AND landing_page_id = $5',
        [section.nazwa, section.tresc, section.obraz_url, section.id, landingPageId]
      );
    }
    
    for (let post of blogPosts) {
      if (post.id) {
        await db.query(
          'UPDATE post_blog SET tytul = $1, tresc = $2, obraz_url = $3, data_aktualizacji = CURRENT_TIMESTAMP WHERE id = $4 AND landing_page_id = $5',
          [post.tytul, post.tresc, post.obraz_url, post.id, landingPageId]
        );
      } else {
        await db.query(
          'INSERT INTO post_blog (landing_page_id, tytul, tresc, obraz_url) VALUES ($1, $2, $3, $4)',
          [landingPageId, post.tytul, post.tresc, post.obraz_url]
        );
      }
    }
    
    await db.query('COMMIT');
    res.json({ message: 'Zawartość strony zaktualizowana pomyślnie' });
  } catch (err) {
    await db.query('ROLLBACK');
    res.status(500).json({ error: 'Błąd serwera' });
  }
};
""",
                    },
                    "models": {
                        "formularz.js": """
const db = require('../config/database');

class Formularz {
  static async create(landingPageId, uzytkownikId, typ, daneFormularza) {
    const query = `
      INSERT INTO formularz (landing_page_id, uzytkownik_id, typ, dane_formularza)
      VALUES ($1, $2, $3, $4)
      RETURNING id
    `;
    const values = [landingPageId, uzytkownikId, typ, JSON.stringify(daneFormularza)];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async getById(id) {
    const query = 'SELECT * FROM formularz WHERE id = $1';
    const result = await db.query(query, [id]);
    return result.rows[0];
  }

  static async updateStatus(id, status) {
    const query = `
      UPDATE formularz
      SET status = $1, data_aktualizacji = CURRENT_TIMESTAMP
      WHERE id = $2
    `;
    await db.query(query, [status, id]);
  }

  static async assignToPracownik(id, pracownikId) {
    const query = `
      UPDATE formularz
      SET pracownik_id = $1, status = 'w_toku', data_przypisania = CURRENT_TIMESTAMP
      WHERE id = $2
    `;
    await db.query(query, [pracownikId, id]);
  }
}

module.exports = Formularz;
""",
                        "komentarz.js": """
const db = require('../config/database');

class Komentarz {
  static async create(formularzId, uzytkownikId, tresc, poleFormularza) {
    const query = `
      INSERT INTO komentarz (formularz_id, uzytkownik_id, tresc, pole_formularza)
      VALUES ($1, $2, $3, $4)
      RETURNING id
    `;
    const values = [formularzId, uzytkownikId, tresc, poleFormularza];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async getByFormularzId(formularzId) {
    const query = `
      SELECT k.*, u.imie, u.nazwisko
      FROM komentarz k
      JOIN uzytkownik u ON k.uzytkownik_id = u.id
      WHERE k.formularz_id = $1
      ORDER BY k.data_utworzenia DESC
    `;
    const result = await db.query(query, [formularzId]);
    return result.rows;
  }
}

module.exports = Komentarz;
""",
                        "landingPage.js": """
const db = require('../config/database');

class LandingPage {
  static async getByDomain(domain) {
    const query = 'SELECT * FROM landing_page WHERE domena = $1';
    const result = await db.query(query, [domain]);
    return result.rows[0];
  }

  static async updateContent(id, sections, blogPosts) {
    await db.query('BEGIN');
    try {
      for (let section of sections) {
        await db.query(
          'UPDATE sekcja SET nazwa = $1, tresc = $2, obraz_url = $3, data_aktualizacji = CURRENT_TIMESTAMP WHERE id = $4 AND landing_page_id = $5',
          [section.nazwa, section.tresc, section.obraz_url, section.id, id]
        );
      }
      
      for (let post of blogPosts) {
        if (post.id) {
          await db.query(
            '
            UPDATE post_blog 
            SET tytul = $1, tresc = $2, obraz_url = $3, data_aktualizacji = CURRENT_TIMESTAMP 
            WHERE id = $4 AND landing_page_id = $5
            ',
            [post.tytul, post.tresc, post.obraz_url, post.id, id]
          );
        } else {
          await db.query(
            'INSERT INTO post_blog (landing_page_id, tytul, tresc, obraz_url) VALUES ($1, $2, $3, $4)',
            [id, post.tytul, post.tresc, post.obraz_url]
          );
        }
      }
      
      await db.query('COMMIT');
    } catch (err) {
      await db.query('ROLLBACK');
      throw err;
    }
  }
}

module.exports = LandingPage;
""",
                        "platnosc.js": """
const db = require('../config/database');

class Platnosc {
  static async create(formularzId, kwota) {
    const query = `
      INSERT INTO platnosc (formularz_id, kwota)
      VALUES ($1, $2)
      RETURNING id
    `;
    const values = [formularzId, kwota];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async updateStatus(id, status) {
    const query = `
      UPDATE platnosc
      SET status = $1, data_platnosci = CURRENT_TIMESTAMP
      WHERE id = $2
    `;
    await db.query(query, [status, id]);
  }

  static async getByFormularzId(formularzId) {
    const query = 'SELECT * FROM platnosc WHERE formularz_id = $1';
    const result = await db.query(query, [formularzId]);
    return result.rows[0];
  }
}

module.exports = Platnosc;
""",
                        "postBlog.js": """
const db = require('../config/database');

class PostBlog {
  static async create(landingPageId, tytul, tresc, obrazUrl) {
    const query = `
      INSERT INTO post_blog (landing_page_id, tytul, tresc, obraz_url)
      VALUES ($1, $2, $3, $4)
      RETURNING id
    `;
    const values = [landingPageId, tytul, tresc, obrazUrl];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async getByLandingPageId(landingPageId, limit = 3) {
    const query = `
      SELECT * FROM post_blog
      WHERE landing_page_id = $1
      ORDER BY data_publikacji DESC
      LIMIT $2
    `;
    const result = await db.query(query, [landingPageId, limit]);
    return result.rows;
  }

  static async update(id, tytul, tresc, obrazUrl) {
    const query = `
      UPDATE post_blog
      SET tytul = $1, tresc = $2, obraz_url = $3, data_aktualizacji = CURRENT_TIMESTAMP
      WHERE id = $4
    `;
    await db.query(query, [tytul, tresc, obrazUrl, id]);
  }
}

module.exports = PostBlog;
""",
                        "powiadomienie.js": """
const db = require('../config/database');

class Powiadomienie {
  static async create(uzytkownikId, tresc) {
    const query = `
      INSERT INTO powiadomienie (uzytkownik_id, tresc)
      VALUES ($1, $2)
      RETURNING id
    `;
    const values = [uzytkownikId, tresc];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async getByUzytkownikId(uzytkownikId) {
    const query = `
      SELECT * FROM powiadomienie
      WHERE uzytkownik_id = $1
      ORDER BY data_utworzenia DESC
    `;
    const result = await db.query(query, [uzytkownikId]);
    return result.rows;
  }

  static async markAsRead(id) {
    const query = `
      UPDATE powiadomienie
      SET przeczytane = true
      WHERE id = $1
    `;
    await db.query(query, [id]);
  }
}

module.exports = Powiadomienie;
""",
                        "sekcja.js": """
const db = require('../config/database');

class Sekcja {
  static async getByLandingPageId(landingPageId) {
    const query = 'SELECT * FROM sekcja WHERE landing_page_id = $1 ORDER BY id';
    const result = await db.query(query, [landingPageId]);
    return result.rows;
  }

  static async update(id, nazwa, tresc, obrazUrl) {
    const query = `
      UPDATE sekcja
      SET nazwa = $1, tresc = $2, obraz_url = $3, data_aktualizacji = CURRENT_TIMESTAMP
      WHERE id = $4
    `;
    await db.query(query, [nazwa, tresc, obrazUrl, id]);
  }
}

module.exports = Sekcja;
""",
                        "uzytkownik.js": """
const db = require('../config/database');
const bcrypt = require('bcrypt');

class Uzytkownik {
  static async create(imie, nazwisko, email, haslo, telefon, adres, firma, nip, typ) {
    const hashedPassword = await bcrypt.hash(haslo, 10);
    const query = `
      INSERT INTO uzytkownik (imie, nazwisko, email, haslo, telefon, adres, firma, nip, typ)
      VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING id
    `;
    const values = [imie, nazwisko, email, hashedPassword, telefon, adres, firma, nip, typ];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async getByEmail(email) {
    const query = 'SELECT * FROM uzytkownik WHERE email = $1';
    const result = await db.query(query, [email]);
    return result.rows[0];
  }

  static async verifyPassword(uzytkownik, haslo) {
    return bcrypt.compare(haslo, uzytkownik.haslo);
  }
}

module.exports = Uzytkownik;
""",
                        "wiadomosc.js": """
const db = require('../config/database');

class Wiadomosc {
  static async create(formularzId, nadawcaId, odbiorcaId, tresc) {
    const query = `
      INSERT INTO wiadomosc (formularz_id, nadawca_id, odbiorca_id, tresc)
      VALUES ($1, $2, $3, $4)
      RETURNING id
    `;
    const values = [formularzId, nadawcaId, odbiorcaId, tresc];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async getByFormularzId(formularzId) {
    const query = `
      SELECT w.*, n.imie AS nadawca_imie, n.nazwisko AS nadawca_nazwisko,
             o.imie AS odbiorca_imie, o.nazwisko AS odbiorca_nazwisko
      FROM wiadomosc w
      JOIN uzytkownik n ON w.nadawca_id = n.id
      JOIN uzytkownik o ON w.odbiorca_id = o.id
      WHERE w.formularz_id = $1
      ORDER BY w.data_wyslania ASC
    `;
    const result = await db.query(query, [formularzId]);
    return result.rows;
  }
}

module.exports = Wiadomosc;
""",
                        "zalacznik.js": """
const db = require('../config/database');

class Zalacznik {
  static async create(formularzId, nazwaPliku, urlPliku, typ) {
    const query = `
      INSERT INTO zalacznik (formularz_id, nazwa_pliku, url_pliku, typ)
      VALUES ($1, $2, $3, $4)
      RETURNING id
    `;
    const values = [formularzId, nazwaPliku, urlPliku, typ];
    const result = await db.query(query, values);
    return result.rows[0].id;
  }

  static async getByFormularzId(formularzId) {
    const query = 'SELECT * FROM zalacznik WHERE formularz_id = $1';
    const result = await db.query(query, [formularzId]);
    return result.rows;
  }
}

module.exports = Zalacznik;
""",
                    },
                    "routes": {
                        "admin.js": """
const express = require('express');
const router = express.Router();
const adminController = require('../controllers/adminController');
const auth = require('../utils/auth');

router.get('/formularze', auth.verifyToken, auth.isAuditorOrWorker, adminController.getFormularzList);
router.post('/formularze/assign', auth.verifyToken, auth.isAuditor, adminController.assignFormularz);
router.post('/formularze/verify', auth.verifyToken, auth.isAuditor, adminController.verifyFormularz);

module.exports = router;
""",
                        "forms.js": """
const express = require('express');
const router = express.Router();
const formController = require('../controllers/formController');
const auth = require('../utils/auth');

router.post('/submit', auth.verifyToken, formController.submitForm);
router.get('/status/:formularzId', auth.verifyToken, formController.getFormStatus);

module.exports = router;
""",
                        "landingPages.js": """
const express = require('express');
const router = express.Router();
const landingPageController = require('../controllers/landingPageController');
const auth = require('../utils/auth');

router.get('/:domain', landingPageController.getLandingPageContent);
router.put('/:landingPageId', auth.verifyToken, auth.isContentAdmin, landingPageController.updateLandingPageContent);

module.exports = router;
""",
                    },
                    "services": {
                        "emailService.js": """
const nodemailer = require('nodemailer');

const transporter = nodemailer.createTransport({
  host: 'smtp.example.com',
  port: 587,
  secure: false,
  auth: {
    user: 'your_email@example.com',
    pass: 'your_password'
  }
});

exports.sendEmail = async (to, subject, text) => {
  try {
    await transporter.sendMail({
      from: '"EnergoCert" <noreply@energocert.pl>',
      to: to,
      subject: subject,
      text: text,
    });
    console.log('Email sent successfully');
  } catch (error) {
    console.error('Error sending email:', error);
  }
};
"""
                    },
                    "utils": {
                        "auth.js": """
const jwt = require('jsonwebtoken');

exports.verifyToken = (req, res, next) => {
  const token = req.headers['x-access-token'];
  if (!token) {
    return res.status(403).json({ message: "Brak tokenu uwierzytelniającego" });
  }
  
  jwt.verify(token, process.env.JWT_SECRET, (err, decoded) => {
    if (err) {
      return res.status(401).json({ message: "Nieautoryzowany dostęp" });
    }
    req.userId = decoded.id;
    next();
  });
};

exports.isAuditor = (req, res, next) => {
  if (req.userType !== 'audytor') {
    return res.status(403).json({ message: "Wymagane uprawnienia audytora" });
  }
  next();
};

exports.isWorker = (req, res, next) => {
  if (req.userType !== 'pracownik') {
    return res.status(403).json({ message: "Wymagane uprawnienia pracownika" });
  }
  next();
};

exports.isAuditorOrWorker = (req, res, next) => {
  if (req.userType !== 'audytor' && req.userType !== 'pracownik') {
    return res.status(403).json({ message: "Wymagane uprawnienia audytora lub pracownika" });
  }
  next();
};

exports.isContentAdmin = (req, res, next) => {
  if (req.userType !== 'admin_tresci') {
    return res.status(403).json({ message: "Wymagane uprawnienia administratora treści" });
  }
  next();
};
"""
                    },
                    "app.js": """
const express = require('express');
const cors = require('cors');
const adminRoutes = require('./routes/admin');
const formRoutes = require('./routes/forms');
const landingPageRoutes = require('./routes/landingPages');

const app = express();

app.use(cors());
app.use(express.json());

app.use('/api/admin', adminRoutes);
app.use('/api/forms', formRoutes);
app.use('/api/landing-pages', landingPageRoutes);

module.exports = app;
""",
                },
                "package.json": """
{
  "name": "energocert-backend",
  "version": "1.0.0",
  "description": "Backend for EnergoCert application",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "bcrypt": "^5.0.1",
    "cors": "^2.8.5",
    "express": "^4.17.1",
    "jsonwebtoken": "^8.5.1",
    "nodemailer": "^6.6.3",
    "pg": "^8.7.1"
  },
  "devDependencies": {
    "nodemon": "^2.0.12"
  }
}
""",
                "server.js": """
const app = require('./src/app');
const port = process.env.PORT || 3000;

app.listen(port, () => {
  console.log(`Server is running on port ${port}`);
});
""",
            },
            "frontend": {
                "public": {
                    "index.html": """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta
      name="description"
      content="EnergoCert - Certyfikaty energetyczne online"
    />
    <link rel="apple-touch-icon" href="%PUBLIC_URL%/logo192.png" />
    <link rel="manifest" href="%PUBLIC_URL%/manifest.json" />
    <title>EnergoCert</title>
</head>
<body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
</body>
</html>
"""
                },
                "src": {
                    "components": {
                        "AdminPanel": {
                            "AuditorPanel.js": """
import React, { useState, useEffect } from 'react';
import { Button, Table, Modal, Form } from '../shared';
import api from '../../services/api';

const AuditorPanel = () => {
  const [formularze, setFormularze] = useState([]);
  const [selectedFormularz, setSelectedFormularz] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [uwagi, setUwagi] = useState('');

  useEffect(() => {
    fetchFormularze();
  }, []);

  const fetchFormularze = async () => {
    try {
      const response = await api.get('/admin/formularze');
      setFormularze(response.data);
    } catch (error) {
      console.error('Błąd podczas pobierania formularzy:', error);
    }
  };

  const handleAssign = async (formularzId, pracownikId) => {
    try {
      await api.post('/admin/formularze/assign', { formularzId, pracownikId });
      fetchFormularze();
    } catch (error) {
      console.error('Błąd podczas przypisywania formularza:', error);
    }
  };

  const handleVerify = async (status) => {
    try {
      await api.post('/admin/formularze/verify', {
        formularzId: selectedFormularz.id,
        status,
        uwagi
      });
      setIsModalOpen(false);
      fetchFormularze();
    } catch (error) {
      console.error('Błąd podczas weryfikacji formularza:', error);
    }
  };

  return (
    <div>
      <h2>Panel Audytora</h2>
      <Table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Typ</th>
            <th>Status</th>
            <th>Data utworzenia</th>
            <th>Akcje</th>
          </tr>
        </thead>
        <tbody>
          {formularze.map((formularz) => (
            <tr key={formularz.id}>
              <td>{formularz.id}</td>
              <td>{formularz.typ}</td>
              <td>{formularz.status}</td>
              <td>{new Date(formularz.data_utworzenia).toLocaleString()}</td>
              <td>
                <Button onClick={() => handleAssign(formularz.id, 1)}>Przypisz</Button>
                <Button onClick={() => { setSelectedFormularz(formularz); setIsModalOpen(true); }}>Weryfikuj</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)}>
        <h3>Weryfikacja formularza</h3>
        <Form>
          <Form.Group>
            <Form.Label>Uwagi</Form.Label>
            <Form.Control as="textarea" rows={3} value={uwagi} onChange={(e) => setUwagi(e.target.value)} />
          </Form.Group>
          <Button onClick={() => handleVerify('zrealizowany')}>Zatwierdź</Button>
          <Button onClick={() => handleVerify('do_poprawy')}>Do poprawy</Button>
        </Form>
      </Modal>
    </div>
  );
};

export default AuditorPanel;
""",
                            "ContentAdminPanel.js": """
import React, { useState, useEffect } from 'react';
import { Button, Form, Table } from '../shared';
import api from '../../services/api';

const ContentAdminPanel = () => {
  const [landingPages, setLandingPages] = useState([]);
  const [selectedPage, setSelectedPage] = useState(null);
  const [sections, setSections] = useState([]);
  const [blogPosts, setBlogPosts] = useState([]);

  useEffect(() => {
    fetchLandingPages();
  }, []);

  const fetchLandingPages = async () => {
    try {
      const response = await api.get('/landing-pages');
      setLandingPages(response.data);
    } catch (error) {
      console.error('Błąd podczas pobierania stron lądowania:', error);
    }
  };

  const handlePageSelect = async (pageId) => {
    try {
      const response = await api.get(`/landing-pages/${pageId}`);
      setSelectedPage(response.data.landingPage);
      setSections(response.data.sections);
      setBlogPosts(response.data.blogPosts);
    } catch (error) {
      console.error('Błąd podczas pobierania szczegółów strony:', error);
    }
  };

  const handleSectionUpdate = (index, field, value) => {
    const updatedSections = [...sections];
    updatedSections[index][field] = value;
    setSections(updatedSections);
  };

  const handleBlogPostUpdate = (index, field, value) => {
    const updatedBlogPosts = [...blogPosts];
    updatedBlogPosts[index][field] = value;
    setBlogPosts(updatedBlogPosts);
  };

  const handleSubmit = async () => {
    try {
      await api.put(`/landing-pages/${selectedPage.id}`, {
        sections,
        blogPosts
      });
      alert('Zmiany zostały zapisane');
    } catch (error) {
      console.error('Błąd podczas aktualizacji strony:', error);
      alert('Wystąpił błąd podczas zapisywania zmian');
    }
  };

  return (
    <div>
      <h2>Panel Administratora Treści</h2>
      <Table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Domena</th>
            <th>Akcje</th>
          </tr>
        </thead>
        <tbody>
          {landingPages.map((page) => (
            <tr key={page.id}>
              <td>{page.id}</td>
              <td>{page.domena}</td>
              <td>
                <Button onClick={() => handlePageSelect(page.id)}>Edytuj</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      {selectedPage && (
        <div>
          <h3>Edycja strony: {selectedPage.domena}</h3>
          <h4>Sekcje</h4>
          {sections.map((section, index) => (
            <Form key={section.id}>
              <Form.Group>
                <Form.Label>Nazwa sekcji</Form.Label>
                <Form.Control
                  type="text"
                  value={section.nazwa}
                  onChange={(e) => handleSectionUpdate(index, 'nazwa', e.target.value)}
                />
              </Form.Group>
              <Form.Group>
                <Form.Label>Treść</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={section.tresc}
                  onChange={(e) => handleSectionUpdate(index, 'tresc', e.target.value)}
                />
              </Form.Group>
              <Form.Group>
                <Form.Label>URL obrazu</Form.Label>
                <Form.Control
                  type="text"
                  value={section.obraz_url}
                  onChange={(e) => handleSectionUpdate(index, 'obraz_url', e.target.value)}
                />
              </Form.Group>
            </Form>
          ))}

          <h4>Posty blogowe</h4>
          {blogPosts.map((post, index) => (
            <Form key={post.id || index}>
              <Form.Group>
                <Form.Label>Tytuł</Form.Label>
                <Form.Control
                  type="text"
                  value={post.tytul}
                  onChange={(e) => handleBlogPostUpdate(index, 'tytul', e.target.value)}
                />
              </Form.Group>
              <Form.Group>
                <Form.Label>Treść</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={post.tresc}
                  onChange={(e) => handleBlogPostUpdate(index, 'tresc', e.target.value)}
                />
              </Form.Group>
              <Form.Group>
                <Form.Label>URL obrazu</Form.Label>
                <Form.Control
                  type="text"
                  value={post.obraz_url}
                  onChange={(e) => handleBlogPostUpdate(index, 'obraz_url', e.target.value)}
                />
              </Form.Group>
            </Form>
          ))}

          <Button onClick={handleSubmit}>Zapisz zmiany</Button>
        </div>
      )}
    </div>
  );
};

export default ContentAdminPanel;
""",
                            "WorkerPanel.js": """
import React, { useState, useEffect } from 'react';
import { Button, Table, Modal, Form } from '../shared';
import api from '../../services/api';

const WorkerPanel = () => {
  const [formularze, setFormularze] = useState([]);
  const [selectedFormularz, setSelectedFormularz] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [komentarz, setKomentarz] = useState('');

  useEffect(() => {
    fetchFormularze();
  }, []);

  const fetchFormularze = async () => {
    try {
      const response = await api.get('/admin/formularze');
      setFormularze(response.data.filter(f => f.status === 'w_toku'));
    } catch (error) {
      console.error('Błąd podczas pobierania formularzy:', error);
    }
  };

  const handleOpenModal = (formularz) => {
    setSelectedFormularz(formularz);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setSelectedFormularz(null);
    setIsModalOpen(false);
    setKomentarz('');
  };

  const handleAddComment = async () => {
    try {
      await api.post('/admin/formularze/komentarz', {
        formularzId: selectedFormularz.id,
        tresc: komentarz
      });
      handleCloseModal();
      fetchFormularze();
    } catch (error) {
      console.error('Błąd podczas dodawania komentarza:', error);
    }
  };

  return (
    <div>
      <h2>Panel Pracownika</h2>
      <Table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Typ</th>
            <th>Data utworzenia</th>
            <th>Akcje</th>
          </tr>
        </thead>
        <tbody>
          {formularze.map((formularz) => (
            <tr key={formularz.id}>
              <td>{formularz.id}</td>
              <td>{formularz.typ}</td>
              <td>{new Date(formularz.data_utworzenia).toLocaleString()}</td>
              <td>
                <Button onClick={() => handleOpenModal(formularz)}>Dodaj komentarz</Button>
              </td>
            </tr>
          ))}
        </tbody>
      </Table>

      <Modal isOpen={isModalOpen} onClose={handleCloseModal}>
        <h3>Dodaj komentarz do formularza</h3>
        <Form>
          <Form.Group>
            <Form.Label>Komentarz</Form.Label>
            <Form.Control
              as="textarea"
              rows={3}
              value={komentarz}
              onChange={(e) => setKomentarz(e.target.value)}
            />
          </Form.Group>
          <Button onClick={handleAddComment}>Dodaj komentarz</Button>
        </Form>
      </Modal>
    </div>
  );
};

export default WorkerPanel;
""",
                        },
                        "Forms": {
                            "ApartmentForm.js": """
import React, { useState } from 'react';
import { Form, Button, Alert } from '../shared';
import api from '../../services/api';

const ApartmentForm = () => {
  const [formData, setFormData] = useState({
    metraz: '',
    czasRealizacji: '',
    dodatkowaPomoc: false,
    cel: '',
    ulica: '',
    numerBudynku: '',
    numerMieszkania: '',
    kodPocztowy: '',
    miasto: '',
    powierzchniaUzytkowa: '',
    wysokoscPomieszczen: '',
    liczbaScianZewnetrznych: '',
    rodzajOgrzewania: '',
    materialScian: '',
    gruboscSciany: '',
    materialIzolacji: '',
    gruboscIzolacji: '',
    klimatyzacja: false,
    fotowoltaika: false,
    balkonTaras: false,
    mieszkanieNaParterze: false,
    mieszkanieNaOstatnimPietrze: false,
    dodatkowyKomentarz: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const response = await api.post('/forms/submit', {
        type: 'apartment',
        formData
      });
      setSubmitResult({
        success: true,
        message: 'Formularz został pomyślnie przesłany.',
        formularzId: response.data.formularzId
      });
    } catch (error) {
      setSubmitResult({
        success: false,
        message: 'Wystąpił błąd podczas przesyłania formularza.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Form onSubmit={handleSubmit}>
      <h2>Formularz dla mieszkania</h2>

      {submitResult && (
        <Alert variant={submitResult.success ? 'success' : 'danger'}>
          {submitResult.message}
          {submitResult.formularzId && (
            <p>ID formularza: {submitResult.formularzId}</p>
          )}
        </Alert>
      )}

      <Form.Group>
        <Form.Label>Metraż</Form.Label>
        <Form.Control as="select" name="metraz" value={formData.metraz} onChange={handleInputChange} required>
          <option value="">Wybierz metraż</option>
          <option value="do50">do 50 m²</option>
          <option value="do70">do 70 m²</option>
          <option value="do100">do 100 m²</option>
          <option value="powyzej100">powyżej 100 m²</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Czas realizacji</Form.Label>
        <Form.Control as="select" name="czasRealizacji" value={formData.czasRealizacji} onChange={handleInputChange} required>
          <option value="">Wybierz czas realizacji</option>
          <option value="standard">Standard do 3 dni</option>
          <option value="express">Express 24h</option>
          <option value="superexpress">Superexpress 6h</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Dodatkowa pomoc w zdobyciu informacji"
          name="dodatkowaPomoc"
          checked={formData.dodatkowaPomoc}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Label>Cel wykonania świadectwa</Form.Label>
        <Form.Control as="select" name="cel" value={formData.cel} onChange={handleInputChange} required>
          <option value="">Wybierz cel</option>
          <option value="sprzedaz">Sprzedaż</option>
          <option value="wynajem">Wynajem</option>
          <option value="oddanie">Oddanie do użytkowania</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Ulica</Form.Label>
        <Form.Control type="text" name="ulica" value={formData.ulica} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Numer budynku</Form.Label>
        <Form.Control type="text" name="numerBudynku" value={formData.numerBudynku} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Numer mieszkania</Form.Label>
        <Form.Control type="text" name="numerMieszkania" value={formData.numerMieszkania} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Kod pocztowy</Form.Label>
        <Form.Control type="text" name="kodPocztowy" value={formData.kodPocztowy} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Miasto</Form.Label>
        <Form.Control type="text" name="miasto" value={formData.miasto} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Powierzchnia użytkowa (m²)</Form.Label>
        <Form.Control type="number" name="powierzchniaUzytkowa" value={formData.powierzchniaUzytkowa} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Wysokość pomieszczeń (cm)</Form.Label>
        <Form.Control type="number" name="wysokoscPomieszczen" value={formData.wysokoscPomieszczen} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Liczba ścian zewnętrznych</Form.Label>
        <Form.Control type="number" name="liczbaScianZewnetrznych" value={formData.liczbaScianZewnetrznych} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Rodzaj ogrzewania</Form.Label>
        <Form.Control as="select" name="rodzajOgrzewania" value={formData.rodzajOgrzewania} onChange={handleInputChange} required>
          <option value="">Wybierz rodzaj ogrzewania</option>
          <option value="gazowe">Gazowe</option>
          <option value="elektryczne">Elektryczne</option>
          <option value="olejowe">Olejowe</option>
          <option value="weglowe">Węglowe</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Materiał ścian zewnętrznych</Form.Label>
        <Form.Control as="select" name="materialScian" value={formData.materialScian} onChange={handleInputChange} required>
          <option value="">Wybierz materiał</option>
          <option value="cegla">Cegła</option>
          <option value="pustak">Pustak</option>
          <option value="beton">Beton</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Grubość ściany zewnętrznej bez izolacji (cm)</Form.Label>
        <Form.Control type="number" name="gruboscSciany" value={formData.gruboscSciany} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Materiał izolacji zewnętrznej</Form.Label>
        <Form.Control as="select" name="materialIzolacji" value={formData.materialIzolacji} onChange={handleInputChange} required>
          <option value="">Wybierz materiał izolacji</option>
          <option value="styropian">Styropian</option>
          <option value="welna">Wełna mineralna</option>
          <option value="pianka">Pianka PUR</option>
          <option value="brak">Brak izolacji</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Grubość materiału izolacyjnego (cm)</Form.Label>
        <Form.Control type="number" name="gruboscIzolacji" value={formData.gruboscIzolacji} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Klimatyzacja"
          name="klimatyzacja"
          checked={formData.klimatyzacja}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Fotowoltaika"
          name="fotowoltaika"
          checked={formData.fotowoltaika}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Balkon/taras"
          name="balkonTaras"
          checked={formData.balkonTaras}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Mieszkanie na parterze"
          name="mieszkanieNaParterze"
          checked={formData.mieszkanieNaParterze}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Mieszkanie na ostatnim piętrze"
          name="mieszkanieNaOstatnimPietrze"
          checked={formData.mieszkanieNaOstatnimPietrze}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Label>Dodatkowy komentarz</Form.Label>
        <Form.Control as="textarea" rows={3} name="dodatkowyKomentarz" value={formData.dodatkowyKomentarz} onChange={handleInputChange} />
      </Form.Group>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Wysyłanie...' : 'Wyślij formularz'}
      </Button>
    </Form>
  );
};

export default ApartmentForm;
""",
                            "AtypicalForm.js": """
import React, { useState } from 'react';
import { Form, Button, Alert } from '../shared';
import api from '../../services/api';

const AtypicalForm = () => {
  const [formData, setFormData] = useState({
    imie: '',
    nazwisko: '',
    email: '',
    telefon: '',
    typNieruchomosci: '',
    ulica: '',
    numerBudynku: '',
    numerLokalu: '',
    kodPocztowy: '',
    miasto: '',
    rokBudowy: '',
    powierzchniaUzytkowa: '',
    dodatkowyKomentarz: '',
    szacunkowaPowierzchnia: 500,
    zgoda: false,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const response = await api.post('/forms/submit', {
        type: 'atypical',
        formData
      });
      setSubmitResult({
        success: true,
        message: 'Formularz został pomyślnie przesłany.',
        formularzId: response.data.formularzId
      });
    } catch (error) {
      setSubmitResult({
        success: false,
        message: 'Wystąpił błąd podczas przesyłania formularza.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const calculateEstimatedPrice = () => {
    const basePrice = 1000;
    const pricePerSquareMeter = 2;
    return basePrice + (formData.szacunkowaPowierzchnia * pricePerSquareMeter);
  };

  return (
    <Form onSubmit={handleSubmit}>
      <h2>Formularz dla budynku niestandardowego</h2>

      {submitResult && (
        <Alert variant={submitResult.success ? 'success' : 'danger'}>
          {submitResult.message}
          {submitResult.formularzId && (
            <p>ID formularza: {submitResult.formularzId}</p>
          )}
        </Alert>
      )}

      <Form.Group>
        <Form.Label>Imię</Form.Label>
        <Form.Control type="text" name="imie" value={formData.imie} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Nazwisko</Form.Label>
        <Form.Control type="text" name="nazwisko" value={formData.nazwisko} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Email</Form.Label>
        <Form.Control type="email" name="email" value={formData.email} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Telefon</Form.Label>
        <Form.Control type="tel" name="telefon" value={formData.telefon} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Typ nieruchomości</Form.Label>
        <Form.Control type="text" name="typNieruchomosci" value={formData.typNieruchomosci} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Ulica</Form.Label>
        <Form.Control type="text" name="ulica" value={formData.ulica} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Numer budynku</Form.Label>
        <Form.Control type="text" name="numerBudynku" value={formData.numerBudynku} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Numer lokalu (opcjonalnie)</Form.Label>
        <Form.Control type="text" name="numerLokalu" value={formData.numerLokalu} onChange={handleInputChange} />
      </Form.Group>

      <Form.Group>
        <Form.Label>Kod pocztowy</Form.Label>
        <Form.Control type="text" name="kodPocztowy" value={formData.kodPocztowy} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Miasto</Form.Label>
        <Form.Control type="text" name="miasto" value={formData.miasto} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Rok budowy</Form.Label>
        <Form.Control type="number" name="rokBudowy" value={formData.rokBudowy} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Powierzchnia użytkowa (m²)</Form.Label>
        <Form.Control type="number" name="powierzchniaUzytkowa" value={formData.powierzchniaUzytkowa} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Dodatkowy komentarz</Form.Label>
        <Form.Control as="textarea" rows={3} name="dodatkowyKomentarz" value={formData.dodatkowyKomentarz} onChange={handleInputChange} />
      </Form.Group>

      <Form.Group>
        <Form.Label>Szacunkowa powierzchnia (500 - 20000 m²)</Form.Label>
        <Form.Control
          type="range"
          name="szacunkowaPowierzchnia"
          min="500"
          max="20000"
          step="100"
          value={formData.szacunkowaPowierzchnia}
          onChange={handleInputChange}
        />
        <Form.Text>Wybrana powierzchnia: {formData.szacunkowaPowierzchnia} m²</Form.Text>
      </Form.Group>

      <Form.Group>
        <Form.Text>Orientacyjna cena: {calculateEstimatedPrice()} zł</Form.Text>
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Akceptuję regulamin i wyrażam zgodę na przetwarzanie danych"
          name="zgoda"
          checked={formData.zgoda}
          onChange={handleInputChange}
          required
        />
      </Form.Group>

      <Button type="submit" disabled={isSubmitting || !formData.zgoda}>
        {isSubmitting ? 'Wysyłanie...' : 'Wyślij zapytanie'}
      </Button>
    </Form>
  );
};

export default AtypicalForm;
""",
                            "CommercialForm.js": """
import React, { useState } from 'react';
import { Form, Button, Alert } from '../shared';
import api from '../../services/api';

const CommercialForm = () => {
  const [formData, setFormData] = useState({
    metraz: '',
    czasRealizacji: '',
    cel: '',
    ulica: '',
    numerBudynku: '',
    numerLokalu: '',
    kodPocztowy: '',
    miasto: '',
    funkcjaLokalu: '',
    powierzchniaUzytkowa: '',
    wysokoscPomieszczen: '',
    liczbaScianZewnetrznych: '',
    rodzajOgrzewania: '',
    materialScian: '',
    gruboscSciany: '',
    materialIzolacji: '',
    gruboscIzolacji: '',
    klimatyzacja: false,
    rekuperacja: false,
    fotowoltaika: false,
    lokalZWiecejNizJednaKondygnacja: false,
    lokalNaParterze: false,
    lokalNaOstatnimPietrze: false,
    lokalLubJegoCzescPodZiemia: false,
    dodatkowyKomentarz: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const response = await api.post('/forms/submit', {
        type: 'commercial',
        formData
      });
      setSubmitResult({
        success: true,
        message: 'Formularz został pomyślnie przesłany.',
        formularzId: response.data.formularzId
      });
    } catch (error) {
      setSubmitResult({
        success: false,
        message: 'Wystąpił błąd podczas przesyłania formularza.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Form onSubmit={handleSubmit}>
      <h2>Formularz dla lokalu użytkowego</h2>

      {submitResult && (
        <Alert variant={submitResult.success ? 'success' : 'danger'}>
          {submitResult.message}
          {submitResult.formularzId && (
            <p>ID formularza: {submitResult.formularzId}</p>
          )}
        </Alert>
      )}

      <Form.Group>
        <Form.Label>Metraż</Form.Label>
        <Form.Control as="select" name="metraz" value={formData.metraz} onChange={handleInputChange} required>
          <option value="">Wybierz metraż</option>
          <option value="do50">do 50 m²</option>
          <option value="do100">do 100 m²</option>
          <option value="do150">do 150 m²</option>
          <option value="do300">do 300 m²</option>
          <option value="do500">do 500 m²</option>
          <option value="do750">do 750 m²</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Czas realizacji</Form.Label>
        <Form.Control as="select" name="czasRealizacji" value={formData.czasRealizacji} onChange={handleInputChange} required>
          <option value="">Wybierz czas realizacji</option>
          <option value="standard">Standard do 5 dni</option>
          <option value="express">Express 24h</option>
          <option value="superexpress">Superexpress 6h</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Cel wykonania świadectwa</Form.Label>
        <Form.Control as="select" name="cel" value={formData.cel} onChange={handleInputChange} required>
          <option value="">Wybierz cel</option>
          <option value="sprzedaz">Sprzedaż</option>
          <option value="wynajem">Wynajem</option>
          <option value="oddanie">Oddanie do użytkowania</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Ulica</Form.Label>
        <Form.Control type="text" name="ulica" value={formData.ulica} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Numer budynku</Form.Label>
        <Form.Control type="text" name="numerBudynku" value={formData.numerBudynku} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Numer lokalu</Form.Label>
        <Form.Control type="text" name="numerLokalu" value={formData.numerLokalu} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Kod pocztowy</Form.Label>
        <Form.Control type="text" name="kodPocztowy" value={formData.kodPocztowy} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Miasto</Form.Label>
        <Form.Control type="text" name="miasto" value={formData.miasto} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Funkcja lokalu</Form.Label>
        <Form.Control as="select" name="funkcjaLokalu" value={formData.funkcjaLokalu} onChange={handleInputChange} required>
          <option value="">Wybierz funkcję</option>
          <option value="biuro">Biuro</option>
          <option value="sklep">Sklep</option>
          <option value="magazyn">Magazyn</option>
          <option value="produkcja">Produkcja</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Powierzchnia użytkowa (m²)</Form.Label>
        <Form.Control type="number" name="powierzchniaUzytkowa" value={formData.powierzchniaUzytkowa} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Wysokość pomieszczeń (cm)</Form.Label>
        <Form.Control type="number" name="wysokoscPomieszczen" value={formData.wysokoscPomieszczen} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Liczba ścian zewnętrznych</Form.Label>
        <Form.Control type="number" name="liczbaScianZewnetrznych" value={formData.liczbaScianZewnetrznych} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Rodzaj ogrzewania</Form.Label>
        <Form.Control as="select" name="rodzajOgrzewania" value={formData.rodzajOgrzewania} onChange={handleInputChange} required>
          <option value="">Wybierz rodzaj ogrzewania</option>
          <option value="gazowe">Gazowe</option>
          <option value="elektryczne">Elektryczne</option>
          <option value="olejowe">Olejowe</option>
          <option value="weglowe">Węglowe</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Materiał ścian zewnętrznych</Form.Label>
        <Form.Control as="select" name="materialScian" value={formData.materialScian} onChange={handleInputChange} required>
          <option value="">Wybierz materiał</option>
          <option value="cegla">Cegła</option>
          <option value="pustak">Pustak</option>
          <option value="beton">Beton</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Grubość ściany zewnętrznej bez izolacji (cm)</Form.Label>
        <Form.Control type="number" name="gruboscSciany" value={formData.gruboscSciany} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Materiał izolacji zewnętrznej</Form.Label>
        <Form.Control as="select" name="materialIzolacji" value={formData.materialIzolacji} onChange={handleInputChange} required>
          <option value="">Wybierz materiał izolacji</option>
          <option value="styropian">Styropian</option>
          <option value="welna">Wełna mineralna</option>
          <option value="pianka">Pianka PUR</option>
          <option value="brak">Brak izolacji</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Grubość materiału izolacyjnego (cm)</Form.Label>
        <Form.Control type="number" name="gruboscIzolacji" value={formData.gruboscIzolacji} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Klimatyzacja"
          name="klimatyzacja"
          checked={formData.klimatyzacja}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Rekuperacja"
          name="rekuperacja"
          checked={formData.rekuperacja}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Fotowoltaika"
          name="fotowoltaika"
          checked={formData.fotowoltaika}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Lokal z więcej niż jedną kondygnacją"
          name="lokalZWiecejNizJednaKondygnacja"
          checked={formData.lokalZWiecejNizJednaKondygnacja}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Lokal na parterze"
          name="lokalNaParterze"
          checked={formData.lokalNaParterze}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Lokal na ostatnim piętrze"
          name="lokalNaOstatnimPietrze"
          checked={formData.lokalNaOstatnimPietrze}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Lokal lub jego część pod ziemią"
          name="lokalLubJegoCzescPodZiemia"
          checked={formData.lokalLubJegoCzescPodZiemia}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Label>Dodatkowy komentarz</Form.Label>
        <Form.Control as="textarea" rows={3} name="dodatkowyKomentarz" value={formData.dodatkowyKomentarz} onChange={handleInputChange} />
      </Form.Group>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Wysyłanie...' : 'Wyślij formularz'}
      </Button>
    </Form>
  );
};

export default CommercialForm;
""",
                            "HouseForm.js": """
import React, { useState } from 'react';
import { Form, Button, Alert } from '../shared';
import api from '../../services/api';

const HouseForm = () => {
  const [formData, setFormData] = useState({
    metraz: '',
    czasRealizacji: '',
    dodatkowaPomoc: false,
    cel: '',
    ulica: '',
    numerBudynku: '',
    kodPocztowy: '',
    miasto: '',
    powierzchniaCałkowita: '',
    powierzchniaUzytkowa: '',
    wysokoscPomieszczen: '',
    rodzajOgrzewania: '',
    materialScian: '',
    gruboscSciany: '',
    materialIzolacji: '',
    gruboscIzolacji: '',
    klimatyzacja: false,
    rekuperacja: false,
    fotowoltaika: false,
    balkonTaras: false,
    buforOgrzewania: false,
    buforCieplejWody: false,
    izolacjaPrzewodowOgrzewania: false,
    izolacjaPrzewodowCieplejWody: false,
    cyrkulacjaCieplejWody: false,
    cyrkulacjaOgrzewania: false,
    piwnica: false,
    poddaszeUzytkowe: false,
    rodzajDachu: '',
    materialyPokryciaDachu: '',
    dodatkowyKomentarz: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const handleInputChange = (event) => {
    const { name, value, type, checked } = event.target;
    setFormData({
      ...formData,
      [name]: type === 'checkbox' ? checked : value
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      const response = await api.post('/forms/submit', {
        type: 'house',
        formData
      });
      setSubmitResult({
        success: true,
        message: 'Formularz został pomyślnie przesłany.',
        formularzId: response.data.formularzId
      });
    } catch (error) {
      setSubmitResult({
        success: false,
        message: 'Wystąpił błąd podczas przesyłania formularza.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Form onSubmit={handleSubmit}>
      <h2>Formularz dla domu</h2>

      {submitResult && (
        <Alert variant={submitResult.success ? 'success' : 'danger'}>
          {submitResult.message}
          {submitResult.formularzId && (
            <p>ID formularza: {submitResult.formularzId}</p>
          )}
        </Alert>
      )}

      <Form.Group>
        <Form.Label>Metraż</Form.Label>
        <Form.Control as="select" name="metraz" value={formData.metraz} onChange={handleInputChange} required>
          <option value="">Wybierz metraż</option>
          <option value="do100">do 100 m²</option>
          <option value="do150">do 150 m²</option>
          <option value="do200">do 200 m²</option>
          <option value="do250">do 250 m²</option>
          <option value="powyzej250">powyżej 250 m²</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Czas realizacji</Form.Label>
        <Form.Control as="select" name="czasRealizacji" value={formData.czasRealizacji} onChange={handleInputChange} required>
          <option value="">Wybierz czas realizacji</option>
          <option value="standard">Standard do 5 dni</option>
          <option value="express">Express 24h</option>
          <option value="superexpress">Superexpress 6h</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Dodatkowa pomoc w zdobyciu informacji"
          name="dodatkowaPomoc"
          checked={formData.dodatkowaPomoc}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Label>Cel wykonania świadectwa</Form.Label>
        <Form.Control as="select" name="cel" value={formData.cel} onChange={handleInputChange} required>
          <option value="">Wybierz cel</option>
          <option value="sprzedaz">Sprzedaż</option>
          <option value="wynajem">Wynajem</option>
          <option value="oddanie">Oddanie do użytkowania</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Ulica</Form.Label>
        <Form.Control type="text" name="ulica" value={formData.ulica} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Numer budynku</Form.Label>
        <Form.Control type="text" name="numerBudynku" value={formData.numerBudynku} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Kod pocztowy</Form.Label>
        <Form.Control type="text" name="kodPocztowy" value={formData.kodPocztowy} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Miasto</Form.Label>
        <Form.Control type="text" name="miasto" value={formData.miasto} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Powierzchnia całkowita (m²)</Form.Label>
        <Form.Control type="number" name="powierzchniaCałkowita" value={formData.powierzchniaCałkowita} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Powierzchnia użytkowa (m²)</Form.Label>
        <Form.Control type="number" name="powierzchniaUzytkowa" value={formData.powierzchniaUzytkowa} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Wysokość pomieszczeń (cm)</Form.Label>
        <Form.Control type="number" name="wysokoscPomieszczen" value={formData.wysokoscPomieszczen} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Rodzaj ogrzewania</Form.Label>
        <Form.Control as="select" name="rodzajOgrzewania" value={formData.rodzajOgrzewania} onChange={handleInputChange} required>
          <option value="">Wybierz rodzaj ogrzewania</option>
          <option value="gazowe">Gazowe</option>
          <option value="elektryczne">Elektryczne</option>
          <option value="olejowe">Olejowe</option>
          <option value="weglowe">Węglowe</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Materiał ścian zewnętrznych</Form.Label>
        <Form.Control as="select" name="materialScian" value={formData.materialScian} onChange={handleInputChange} required>
          <option value="">Wybierz materiał</option>
          <option value="cegla">Cegła</option>
          <option value="pustak">Pustak</option>
          <option value="beton">Beton</option>
          <option value="drewno">Drewno</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Grubość ściany zewnętrznej bez izolacji (cm)</Form.Label>
        <Form.Control type="number" name="gruboscSciany" value={formData.gruboscSciany} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Materiał izolacji zewnętrznej</Form.Label>
        <Form.Control as="select" name="materialIzolacji" value={formData.materialIzolacji} onChange={handleInputChange} required>
          <option value="">Wybierz materiał izolacji</option>
          <option value="styropian">Styropian</option>
          <option value="welna">Wełna mineralna</option>
          <option value="pianka">Pianka PUR</option>
          <option value="brak">Brak izolacji</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Grubość materiału izolacyjnego (cm)</Form.Label>
        <Form.Control type="number" name="gruboscIzolacji" value={formData.gruboscIzolacji} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Klimatyzacja"
          name="klimatyzacja"
          checked={formData.klimatyzacja}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Rekuperacja"
          name="rekuperacja"
          checked={formData.rekuperacja}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Fotowoltaika"
          name="fotowoltaika"
          checked={formData.fotowoltaika}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Balkon/taras"
          name="balkonTaras"
          checked={formData.balkonTaras}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Bufor/zbiornik ogrzewania"
          name="buforOgrzewania"
          checked={formData.buforOgrzewania}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Bufor/zbiornik ciepłej wody"
          name="buforCieplejWody"
          checked={formData.buforCieplejWody}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Izolacja przewodów instalacji ogrzewania"
          name="izolacjaPrzewodowOgrzewania"
          checked={formData.izolacjaPrzewodowOgrzewania}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Izolacja przewodów instalacji ciepłej wody"
          name="izolacjaPrzewodowCieplejWody"
          checked={formData.izolacjaPrzewodowCieplejWody}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Cyrkulacja ciepłej wody"
          name="cyrkulacjaCieplejWody"
          checked={formData.cyrkulacjaCieplejWody}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Cyrkulacja ogrzewania"
          name="cyrkulacjaOgrzewania"
          checked={formData.cyrkulacjaOgrzewania}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Piwnica"
          name="piwnica"
          checked={formData.piwnica}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Check
          type="checkbox"
          label="Poddasze użytkowe"
          name="poddaszeUzytkowe"
          checked={formData.poddaszeUzytkowe}
          onChange={handleInputChange}
        />
      </Form.Group>

      <Form.Group>
        <Form.Label>Rodzaj dachu</Form.Label>
        <Form.Control as="select" name="rodzajDachu" value={formData.rodzajDachu} onChange={handleInputChange} required>
          <option value="">Wybierz rodzaj dachu</option>
          <option value="plaski">Płaski</option>
          <option value="skosny">Skośny</option>
          <option value="mansardowy">Mansardowy</option>
          <option value="inne">Inne</option>
        </Form.Control>
      </Form.Group>

      <Form.Group>
        <Form.Label>Materiały pokrycia i izolacji dachu</Form.Label>
        <Form.Control type="text" name="materialyPokryciaDachu" value={formData.materialyPokryciaDachu} onChange={handleInputChange} required />
      </Form.Group>

      <Form.Group>
        <Form.Label>Dodatkowy komentarz</Form.Label>
        <Form.Control as="textarea" rows={3} name="dodatkowyKomentarz" value={formData.dodatkowyKomentarz} onChange={handleInputChange} />
      </Form.Group>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? 'Wysyłanie...' : 'Wyślij formularz'}
      </Button>
    </Form>
  );
};

export default HouseForm;
""",
                        },
                        "LandingPage": {
                            "BlogSection.js": """
import React from 'react';
import { Card } from '../shared';

const BlogSection = ({ posts }) => {
  return (
    <section className="py-16 bg-teal-500 text-white">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold mb-8 text-center">Najnowsze artykuły</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {posts.map((post) => (
            <Card key={post.id} className="bg-white text-gray-800">
              <img src={post.obraz_url} alt={post.tytul} className="w-full h-48 object-cover" />
              <div className="p-4">
                <h3 className="text-xl font-semibold mb-2">{post.tytul}</h3>
                <p className="text-gray-600">{post.tresc.substring(0, 100)}...</p>
                <a href="#" className="mt-4 inline-block text-teal-500 hover:text-teal-600">Czytaj więcej</a>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default BlogSection;
""",
                            "ContactSection.js": """
import React, { useState } from 'react';
import { Form, Button, Alert } from '../shared';

const ContactSection = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState(null);

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setFormData({
      ...formData,
      [name]: value
    });
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setIsSubmitting(true);
    try {
      // Tutaj powinno być wysłanie formularza do API
      await new Promise(resolve => setTimeout(resolve, 1000)); // Symulacja opóźnienia
      setSubmitResult({
        success: true,
        message: 'Wiadomość została wysłana pomyślnie.'
      });
    } catch (error) {
      setSubmitResult({
        success: false,
        message: 'Wystąpił błąd podczas wysyłania wiadomości.'
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section id="kontakt" className="py-16 bg-white">
      <div className="container mx-auto px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-3xl font-bold mb-8 text-center">Skontaktuj się z nami</h2>
          {submitResult && (
            <Alert variant={submitResult.success ? 'success' : 'danger'}>
              {submitResult.message}
            </Alert>
          )}
          <Form onSubmit={handleSubmit}>
            <Form.Group>
              <Form.Label>Imię i nazwisko</Form.Label>
              <Form.Control
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Adres e-mail</Form.Label>
              <Form.Control
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Temat</Form.Label>
              <Form.Control
                type="text"
                name="subject"
                value={formData.subject}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            <Form.Group>
              <Form.Label>Wiadomość</Form.Label>
              <Form.Control
                as="textarea"
                rows={5}
                name="message"
                value={formData.message}
                onChange={handleInputChange}
                required
              />
            </Form.Group>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Wysyłanie...' : 'Wyślij wiadomość'}
            </Button>
          </Form>
        </div>
      </div>
    </section>
  );
};

export default ContactSection;
""",
                            "Footer.js": """
import React from 'react';

const Footer = () => {
  return (
    <footer className="bg-gray-800 text-white py-8">
      <div className="container mx-auto px-4">
        <div className="flex flex-wrap justify-between">
          <div className="w-full md:w-1/4 mb-6 md:mb-0">
            <h3 className="text-xl font-bold mb-4">EnergoCert</h3>
            <p className="text-sm">Profesjonalne certyfikaty energetyczne dla Twojej nieruchomości.</p>
          </div>
          <div className="w-full md:w-1/4 mb-6 md:mb-0">
            <h4 className="text-lg font-semibold mb-4">Szybkie linki</h4>
            <ul className="text-sm">
              <li className="mb-2"><a href="#" className="hover:text-teal-300">Strona główna</a></li>
              <li className="mb-2"><a href="#" className="hover:text-teal-300">O nas</a></li>
              <li className="mb-2"><a href="#" className="hover:text-teal-300">Usługi</a></li>
              <li className="mb-2"><a href="#" className="hover:text-teal-300">Kontakt</a></li>
            </ul>
          </div>
          <div className="w-full md:w-1/4 mb-6 md:mb-0">
            <h4 className="text-lg font-semibold mb-4">Kontakt</h4>
            <ul className="text-sm">
              <li className="mb-2">ul. Przykładowa 123</li>
              <li className="mb-2">00-000 Warszawa</li>
              <li className="mb-2">Tel: +48 123 456 789</li>
              <li className="mb-2">Email: kontakt@energocert.pl</li>
            </ul>
          </div>
          <div className="w-full md:w-1/4">
            <h4 className="text-lg font-semibold mb-4">Śledź nas</h4>
            <div className="flex space-x-4">
              <a href="#" className="text-white hover:text-teal-300">
                <i className="fab fa-facebook-f"></i>
              </a>
              <a href="#" className="text-white hover:text-teal-300">
                <i className="fab fa-twitter"></i>
              </a>
              <a href="#" className="text-white hover:text-teal-300">
                <i className="fab fa-linkedin-in"></i>
              </a>
              <a href="#" className="text-white hover:text-teal-300">
                <i className="fab fa-instagram"></i>
              </a>
            </div>
          </div>
        </div>
        <div className="border-t border-gray-700 mt-8 pt-8 text-sm text-center">
          <p>&copy; 2023 EnergoCert. Wszelkie prawa zastrzeżone.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
""",
                            "Header.js": """
import React, { useState, useEffect } from 'react';
import { Button } from '../shared';

const Header = () => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 50);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navItems = [
    { name: 'Strona Główna', href: '#home' },
    { name: 'O nas', href: '#about' },
    { name: 'Jak to działa', href: '#how-it-works' },
    { name: 'Formularze', href: '#forms' },
    { name: 'Cennik', href: '#pricing' },
    { name: 'Blog', href: '#blog' },
    { name: 'Kontakt', href: '#contact' },
  ];

  return (
    <header className={`fixed w-full z-50 transition-all duration-300 ${isScrolled ? 'bg-teal-600' : 'bg-transparent'}`}>
      <div className="container mx-auto px-4">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center">
            <a href="#" className="text-white text-2xl font-bold">EnergoCert</a>
          </div>
          <nav className="hidden md:flex space-x-4">
            {navItems.map((item) => (
              <a
                key={item.name}
                href={item.href}
                className="text-white hover:text-yellow-300 px-3 py-2 rounded-md text-sm font-medium"
              >
                {item.name}
              </a>
            ))}
          </nav>
          <div className="hidden md:block">
            <Button className="bg-yellow-400 hover:bg-yellow-500 text-gray-900">
              Uzyskaj certyfikat
            </Button>
          </div>
          <div className="md:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="text-white hover:text-yellow-300 focus:outline-none"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
      {isMobileMenuOpen && (
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
            {navItems.map((item) => (
              <a
                key={item.name}
                href={item.href}
                className="text-white hover:bg-teal-700 hover:text-white block px-3 py-2 rounded-md text-base font-medium"
              >
                {item.name}
              </a>
            ))}
          </div>
          <div className="pt-4 pb-3 border-t border-teal-700">
            <div className="flex items-center px-5">
              <Button className="w-full bg-yellow-400 hover:bg-yellow-500 text-gray-900">
                Uzyskaj certyfikat
              </Button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
};

export default Header;
""",
                            "HeroSection.js": """
import React, { useState, useEffect } from 'react';
import { Button } from '../shared';

const HeroSection = () => {
  const [currentSlide, setCurrentSlide] = useState(0);

  const slides = [
    {
      title: "Uzyskaj certyfikat energetyczny",
      subtitle: "bez wychodzenia z domu",
      description: "Profesjonalne usługi, szybka realizacja i intuicyjny system. Wypełnij formularz online, a my zajmiemy się resztą.",
      image: "https://images.unsplash.com/photo-1460472178825-e5240623afd5?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=1350&q=80"
    },
    {
      title: "Oszczędzaj energię",
      subtitle: "i dbaj o środowisko",
      description: "Dowiedz się, jak efektywnie zarządzać energią w swoim domu lub firmie. Zainwestuj w przyszłość już dziś!",
      image: "https://images.unsplash.com/photo-1497366216548-37526070297c?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80"
    },
    {
      title: "Eksperci w dziedzinie",
      subtitle: "certyfikacji energetycznej",
      description: "Nasz zespół specjalistów pomoże Ci w każdym kroku procesu. Skorzystaj z naszego doświadczenia!",
      image: "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?ixlib=rb-1.2.1&auto=format&fit=crop&w=1350&q=80"
    }
  ];

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentSlide((prevSlide) => (prevSlide + 1) % slides.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="relative h-screen flex items-center justify-center overflow-hidden">
      {slides.map((slide, index) => (
        <div
          key={index}
          className={`absolute inset-0 transition-opacity duration-1000 ${
            index === currentSlide ? 'opacity-100' : 'opacity-0'
          }`}
        >
          <div className="absolute inset-0 bg-black opacity-50"></div>
          <img
            src={slide.image}
            alt={slide.title}
            className="absolute inset-0 w-full h-full object-cover"
          />
          <div className="relative z-10 text-center text-white px-4">
            <h1 className="text-4xl md:text-6xl font-bold mb-4">
              {slide.title}
              <span className="block text-yellow-400">{slide.subtitle}</span>
            </h1>
            <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto">
              {slide.description}
            </p>
            <Button className="bg-yellow-400 hover:bg-yellow-500 text-gray-900 text-lg px-8 py-3">
              Zamów teraz
            </Button>
          </div>
        </div>
      ))}
      <div className="absolute bottom-5 left-0 right-0 flex justify-center space-x-2">
        {slides.map((_, index) => (
          <button
            key={index}
            className={`w-3 h-3 rounded-full ${
              index === currentSlide ? 'bg-yellow-400' : 'bg-white bg-opacity-50'
            }`}
            onClick={() => setCurrentSlide(index)}
          ></button>
        ))}
      </div>
    </section>
  );
};

export default HeroSection;
""",
                            "HowItWorksSection.js": """
import React from 'react';
import { Card } from '../shared';

const HowItWorksSection = () => {
  const steps = [
    {
      title: "Zarejestruj się i zapłać",
      description: "Opłać zamówienie online i zarejestruj swoje konto.",
      icon: "fas fa-user-plus"
    },
    {
      title: "Wypełnij formularz",
      description: "Wprowadź dane dotyczące swojego budynku. Jeśli potrzebujesz pomocy, skontaktuj się z nami!",
      icon: "fas fa-file-alt"
    },
    {
      title: "Otrzymaj certyfikat",
      description: "Odbierz certyfikat energetyczny bez wychodzenia z domu – szybko i wygodnie.",
      icon: "fas fa-certificate"
    }
  ];

  return (
    <section id="jak-to-dziala" className="py-16 bg-gray-100">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold mb-8 text-center">Jak to działa</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, index) => (
            <Card key={index} className="text-center p-6">
              <div className="text-4xl text-teal-500 mb-4">
                <i className={step.icon}></i>
              </div>
              <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
              <p className="text-gray-600">{step.description}</p>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default HowItWorksSection;
""",
                            "PricingSection.js": """
import React from 'react';
import { Card, Button } from '../shared';

const PricingSection = () => {
  const pricingPlans = [
    {
      name: "Certyfikat dla mieszkania",
      price: "499 zł",
      features: [
        "Do 100m²",
        "Czas realizacji: 2 dni",
        "Konsultacja online"
      ]
    },
    {
      name: "Certyfikat dla domu",
      price: "699 zł",
      features: [
        "Do 200m²",
        "Czas realizacji: 3 dni",
        "Konsultacja telefoniczna"
      ]
    },
    {
      name: "Certyfikat dla lokalu użytkowego",
      price: "999 zł",
      features: [
        "Do 500m²",
        "Czas realizacji: 5 dni",
        "Osobisty doradca"
      ]
    }
  ];

  return (
    <section id="cennik" className="py-16 bg-gray-100">
      <div className="container mx-auto px-4">
        <h2 className="text-3xl font-bold mb-8 text-center">Cennik</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {pricingPlans.map((plan, index) => (
            <Card key={index} className="text-center p-6">
              <h3 className="text-xl font-semibold mb-4">{plan.name}</h3>
              <p className="text-3xl font-bold text-teal-600 mb-6">{plan.price}</p>
              <ul className="mb-6 space-y-2">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center justify-center">
                    <svg className="w-4 h-4 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                    </svg>
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className="w-full bg-teal-500 hover:bg-teal-600 text-white">Wybierz plan</Button>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
};

export default PricingSection;
""",
                            "index.js": """
export { default as Header } from './Header';
export { default as HeroSection } from './HeroSection';
export { default as HowItWorksSection } from './HowItWorksSection';
export { default as PricingSection } from './PricingSection';
export { default as BlogSection } from './BlogSection';
export { default as ContactSection } from './ContactSection';
export { default as Footer } from './Footer';
""",
                        },
                        "shared": {
                            "Alert.js": """
import React from 'react';

const Alert = ({ variant, children }) => {
  const baseClasses = 'p-4 mb-4 rounded-md';
  const variantClasses = {
    success: 'bg-green-100 text-green-700',
    danger: 'bg-red-100 text-red-700',
    warning: 'bg-yellow-100 text-yellow-700',
    info: 'bg-blue-100 text-blue-700',
  };

  return (
    <div className={`${baseClasses} ${variantClasses[variant]}`} role="alert">
      {children}
    </div>
  );
};

export default Alert;
""",
                            "Button.js": """
import React from 'react';

const Button = ({ children, className, ...props }) => {
  return (
    <button
      className={`px-4 py-2 rounded-md font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 ${className}`}
      {...props}
    >
      {children}
    </button>
  );
};

export default Button;
""",
                            "Card.js": """
import React from 'react';

const Card = ({ children, className, ...props }) => {
  return (
    <div
      className={`bg-white shadow-md rounded-lg overflow-hidden ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export default Card;
""",
                            "Form.js": """
import React from 'react';

const Form = ({ children, ...props }) => {
  return (
    <form {...props}>
      {children}
    </form>
  );
};

const FormGroup = ({ children }) => {
  return <div className="mb-4">{children}</div>;
};

const FormLabel = ({ children, htmlFor }) => {
  return (
    <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor={htmlFor}>
      {children}
    </label>
  );
};

const FormControl = React.forwardRef(({ className, ...props }, ref) => {
  return (
    <input
      className={`shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline ${className}`}
      ref={ref}
      {...props}
    />
  );
});

const FormCheck = ({ children, ...props }) => {
  return (
    <div className="flex items-center">
      <input
        type="checkbox"
        className="form-checkbox h-5 w-5 text-teal-600"
        {...props}
      />
      <label className="ml-2 block text-gray-700">{children}</label>
    </div>
  );
};

Form.Group = FormGroup;
Form.Label = FormLabel;
Form.Control = FormControl;
Form.Check = FormCheck;

export default Form;
""",
                            "Modal.js": """
import React from 'react';

const Modal = ({ isOpen, onClose, children }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed z-10 inset-0 overflow-y-auto">
      <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div className="fixed inset-0 transition-opacity" aria-hidden="true">
          <div className="absolute inset-0 bg-gray-500 opacity-75"></div>
        </div>

        <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>

        <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            {children}
          </div>
          <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              type="button"
              className="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
              onClick={onClose}
            >
              Zamknij
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Modal;
""",
                            "Table.js": """
import React from 'react';

const Table = ({ children }) => {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        {children}
      </table>
    </div>
  );
};

export default Table;
""",
                            "index.js": """
export { default as Alert } from './Alert';
export { default as Button } from './Button';
export { default as Card } from './Card';
export { default as Form } from './Form';
export { default as Modal } from './Modal';
export { default as Table } from './Table';
""",
                        },
                        "AdminPanel.js": """
import React, { useState } from 'react';
import AuditorPanel from './AdminPanel/AuditorPanel';
import WorkerPanel from './AdminPanel/WorkerPanel';
import ContentAdminPanel from './AdminPanel/ContentAdminPanel';

const AdminPanel = ({ userType }) => {
  const [activeTab, setActiveTab] = useState('auditor');

  const renderPanel = () => {
    switch (activeTab) {
      case 'auditor':
        return <AuditorPanel />;
      case 'worker':
        return <WorkerPanel />;
      case 'content':
        return <ContentAdminPanel />;
      default:
        return null;
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Panel Administracyjny</h1>
      <div className="mb-6">
        <button
          className={`mr-4 px-4 py-2 rounded ${activeTab === 'auditor' ? 'bg-teal-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setActiveTab('auditor')}
        >
          Panel Audytora
        </button>
        <button
          className={`mr-4 px-4 py-2 rounded ${activeTab === 'worker' ? 'bg-teal-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setActiveTab('worker')}
        >
          Panel Pracownika
        </button>
        <button
          className={`px-4 py-2 rounded ${activeTab === 'content' ? 'bg-teal-500 text-white' : 'bg-gray-200'}`}
          onClick={() => setActiveTab('content')}
        >
          Panel Administratora Treści
        </button>
      </div>
      {renderPanel()}
    </div>
  );
};

export default AdminPanel;
""",
                        "LandingPage.js": """
import React from 'react';
import {
  Header,
  HeroSection,
  HowItWorksSection,
  PricingSection,
  BlogSection,
  ContactSection,
  Footer
} from './LandingPage';

const LandingPage = ({ content }) => {
  return (
    <div>
      <Header />
      <HeroSection slides={content.heroSlides} />
      <HowItWorksSection steps={content.howItWorksSteps} />
      <PricingSection plans={content.pricingPlans} />
      <BlogSection posts={content.blogPosts} />
      <ContactSection />
      <Footer />
    </div>
  );
};

export default LandingPage;
""",
                    },
                    "services": {
                        "api.js": """
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL || 'http://localhost:3000/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

api.interceptors.response.use((response) => {
  return response;
}, (error) => {
  if (error.response && error.response.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
  }
  return Promise.reject(error);
});

export default api;
""",
                        "auth.js": """
import api from './api';

export const login = async (email, password) => {
  try {
    const response = await api.post('/auth/login', { email, password });
    localStorage.setItem('token', response.data.token);
    return response.data;
  } catch (error) {
    throw error.response.data;
  }
};

export const logout = () => {
  localStorage.removeItem('token');
};

export const register = async (userData) => {
  try {
    const response = await api.post('/auth/register', userData);
    return response.data;
  } catch (error) {
    throw error.response.data;
  }
};

export const getCurrentUser = async () => {
  try {
    const response = await api.get('/auth/me');
    return response.data;
  } catch (error) {
    throw error.response.data;
  }
};
""",
                    },
                    "App.js": """
import React from 'react';
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';
import LandingPage from './components/LandingPage';
import AdminPanel from './components/AdminPanel';
import ApartmentForm from './components/Forms/ApartmentForm';
import HouseForm from './components/Forms/HouseForm';
import CommercialForm from './components/Forms/CommercialForm';
import AtypicalForm from './components/Forms/AtypicalForm';

function App() {
  return (
    <Router>
      <Switch>
        <Route exact path="/" component={LandingPage} />
        <Route path="/admin" component={AdminPanel} />
        <Route path="/form/apartment" component={ApartmentForm} />
        <Route path="/form/house" component={HouseForm} />
        <Route path="/form/commercial" component={CommercialForm} />
        <Route path="/form/atypical" component={AtypicalForm} />
      </Switch>
    </Router>
  );
}

export default App;
""",
                    "index.js": """
import React from 'react';
import ReactDOM from 'react-dom';
import './index.css';
import App from './App';

ReactDOM.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);
""",
                },
                "package.json": """
{
  "name": "energocert-frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "@testing-library/jest-dom": "^5.11.4",
    "@testing-library/react": "^11.1.0",
    "@testing-library/user-event": "^12.1.10",
    "axios": "^0.21.1",
    "react": "^17.0.2",
    "react-dom": "^17.0.2",
    "react-router-dom": "^5.2.0",
    "react-scripts": "4.0.3",
    "web-vitals": "^1.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  },
  "devDependencies": {
    "autoprefixer": "^10.2.5",
    "postcss": "^8.2.15",
    "tailwindcss": "^2.1.2"
  }
}
""",
            },
        }
    }

    create_directory_structure(".", structure)


if __name__ == "__main__":
    create_structure()
