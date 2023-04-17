// const headerTemplate = document.createElement('template');

// headerTemplate

class Header extends HTMLElement {
  constructor() {
    super();
  }

  connectedCallback() {
    this.innerHTML = `
    <link rel="stylesheet" type="text/css" href="main.css">
    <header>
      <nav>
        <ul>
          <li><a href="../index.html">Home</a></li>
          <li><a href="../CV.html">CV</a></li>
          <li><a href="../CV/publications.html">Publications</a></li>
          <li><a href="../CV/conferences.html">Conferences</a></li>
          <li><a href="../Reviews.html">Reviews</a></li>
        </ul>
      </nav>
    </header>
  `;
  }
}

customElements.define('header-component', Header);